"""Step 2 of the real-model test: evaluate every cascade design offline.

Reads the outputs stored by run_models.py and writes realtest/REPORT_<task>.md.

Method, the same as in the simulations:
- the requests are split once, with a fixed seed, into a calibration half and a test half;
- each model's raw confidence is calibrated on the calibration half (quantile bins);
- the threshold is the cheapest one that keeps calibration accuracy within the tolerance of
  the largest model alone; the similarity threshold of the lookup stage is chosen on the
  calibration half too;
- every reported figure comes from the test half, with bootstrap confidence intervals.

Usage:
    python -m realtest.analyze --task departments
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import pathlib
import time

import numpy as np

from funnel.confidence import calibration_chi2
from funnel.routing import NEVER, BinnedCalibrator

from . import data
from .lookup import HistoryLookup
from .run_models import DEFAULT_SHOTS, OUTPUTS, match_category, variant

HERE = pathlib.Path(__file__).resolve().parent
RULE_THRESHOLD = 5.0
SIMILARITIES = tuple(np.round(np.arange(0.30, 0.9001, 0.05), 2)) + (2.0,)     # 2.0 = the lookup never answers
BOOTSTRAP = 2000


def load_outputs(task, shots: int):
    """Returns {model: {item: row}} for one workload and prompt variant.

    The answer is read again from the stored raw response, so a better reading of the
    answers never requires running the models again.
    """
    rows = {}
    names = list(task.categories)
    for path in sorted((OUTPUTS / task.name / variant(shots)).glob("*.jsonl")):
        by_item = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if line:
                row = json.loads(line)
                row["answer"] = match_category(row["response"], names, task.aliases)
                row["correct"] = row["answer"] == row["label"]
                row["confidence"] = math.exp(sum(row["token_logprobs"])) if row["answer"] >= 0 else 0.0
                by_item[row["item"]] = row
        if by_item:
            rows[next(iter(by_item.values()))["model"]] = by_item
    return rows


def auroc(signal, correct) -> float:
    """Probability that a right answer has a higher confidence than a wrong one."""
    correct = np.asarray(correct, bool)
    if correct.all() or not correct.any():
        return float("nan")
    order = np.argsort(signal, kind="mergesort")
    ranks = np.empty(len(signal))
    ranks[order] = np.arange(1, len(signal) + 1)
    for value in np.unique(signal):                       # average ranks over ties
        tied = signal == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    n_pos, n_neg = correct.sum(), (~correct).sum()
    return float((ranks[correct].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def cascade(correct, confidence, costs, stages, threshold, rule=None):
    """Per-request outcome of a cascade: (answered correctly, compute spent, stage that answered)."""
    n = correct.shape[1]
    done = np.zeros(n, bool)
    ok = np.zeros(n, bool)
    spent = np.zeros(n)
    where = np.full(n, -1)
    offset = 0
    if rule is not None:
        rule_cost, fired, rule_correct = rule
        spent += rule_cost
        ok[fired] = rule_correct[fired]
        where[fired] = 0
        done |= fired
        offset = 1
    for j, f in enumerate(stages):
        active = ~done
        spent += active * costs[f]
        stop = active & ((confidence[f] >= threshold) | (j == len(stages) - 1))
        ok[stop] = correct[f][stop]
        where[stop] = offset + j
        done |= stop
    return ok, spent, where


def choose_threshold(correct, confidence, costs, stages, target, grid, rule=None):
    best = (NEVER, np.inf)
    for threshold in grid:
        ok, spent, _ = cascade(correct, confidence, costs, stages, threshold, rule)
        if ok.mean() >= target and spent.mean() < best[1]:
            best = (float(threshold), float(spent.mean()))
    return best


def interval(values):
    lo, hi = np.percentile(values, [2.5, 97.5])
    return float(lo), float(hi)


def fmt_pct(x, signed=False):
    return f"{100 * x:+.0f}%" if signed else f"{100 * x:.0f}%"


def fmt_points(x, lo, hi):
    return f"{100 * x:+.1f} ({100 * lo:+.1f} to {100 * hi:+.1f})"


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def analyze(task_name="banking77", shots=DEFAULT_SHOTS, tolerance=0.005, n_bins=15, seed=data.SEED) -> str:
    task = data.load(task_name)
    train, test = task.train, task.test
    outputs = load_outputs(task, shots)
    if len(outputs) < 2:
        raise SystemExit(f"Need the stored outputs of at least two models in {OUTPUTS / task_name / variant(shots)}. "
                         f"Run: python -m realtest.run_models --task {task_name} --shots {shots}")
    common = sorted(set.intersection(*(set(rows) for rows in outputs.values())))
    order = [int(i) for i in data.select(len(test), None) if int(i) in set(common)]
    n = len(order)
    if n < 200:
        raise SystemExit(f"Only {n} requests are stored for every model: too few to analyse.")

    names = sorted(outputs, key=lambda m: np.mean([outputs[m][i]["compute_seconds"] for i in order]))
    correct = np.array([[outputs[m][i]["correct"] for i in order] for m in names], bool)
    signal = np.array([[outputs[m][i]["confidence"] for i in order] for m in names], float)
    costs = np.array([np.mean([outputs[m][i]["compute_seconds"] for i in order]) for m in names])
    labels = np.array([test[i][1] for i in order])
    calibration = data.split(n, seed)
    held_out = ~calibration
    rng = np.random.default_rng([seed, 2])

    # deterministic lookup stage, measured: its thresholds come from the calibration half only
    history = HistoryLookup([t for t, _ in train], [y for _, y in train])
    tick = time.perf_counter()
    guess, score, agree = history.query([test[i][0] for i in order])
    lookup_cost = (time.perf_counter() - tick) / n
    lookup_correct = guess == labels

    def fired_at(similarity):
        return agree & (score >= similarity)

    # calibrated confidence
    confidence = np.zeros_like(signal)
    for f in range(len(names)):
        fitted = BinnedCalibrator(n_bins).fit(signal[f][calibration], correct[f][calibration])
        confidence[f] = fitted.predict(signal[f])
    grid = np.append(np.unique(np.round(confidence[:, calibration], 4)), NEVER)

    def evaluate(stages, with_lookup):
        """Thresholds on the calibration half; per-request outcomes on the test half."""
        large = stages[-1]
        target = correct[large][calibration].mean() - tolerance
        best = None
        for similarity in (SIMILARITIES if with_lookup else (None,)):
            rule = None if similarity is None else (lookup_cost, fired_at(similarity)[calibration],
                                                    lookup_correct[calibration])
            threshold, cost = choose_threshold(correct[:, calibration], confidence[:, calibration], costs, stages,
                                               target, grid, rule)
            if best is None or cost < best[2]:
                best = (similarity, threshold, cost)
        similarity, threshold, _ = best
        rule = None if similarity is None else (lookup_cost, fired_at(similarity)[held_out], lookup_correct[held_out])
        ok, spent, where = cascade(correct[:, held_out], confidence[:, held_out], costs, stages, threshold, rule)
        return {"threshold": threshold, "similarity": similarity, "ok": ok, "spent": spent, "where": where}

    n_test = int(held_out.sum())
    resamples = rng.integers(0, n_test, size=(BOOTSTRAP, n_test))

    def saving(run, large):
        return 1 - run["spent"].mean() / costs[large]

    def saving_interval(run, large):
        return interval(1 - run["spent"][resamples].mean(axis=1) / costs[large])

    def saving_gain(run, base, large):
        """Points of saving gained by `run` over `base`, with a paired bootstrap interval."""
        diff = (base["spent"] - run["spent"]) / costs[large]
        return float(diff.mean()), *interval(diff[resamples].mean(axis=1))

    def accuracy_delta(run, large):
        diff = run["ok"].astype(float) - correct[large][held_out].astype(float)
        return float(diff.mean()), *interval(diff[resamples].mean(axis=1))

    out = ["# Real-model test: report", "",
           f"Workload: {task.title}. {n} requests. "
           f"Calibration half {int(calibration.sum())}, test half {n_test}. Every figure below is measured on "
           "the test half; intervals are 95% bootstrap intervals.", "",
           f"The models answer with the name of the {task.noun}. "
           + (f"They are shown the list with {shots} example request{'s' if shots > 1 else ''} for each, "
              "taken from the history." if shots else "They are shown the list and no example requests."), "",
           f"This file is generated by `python -m realtest.analyze --task {task_name} --shots {shots}` from the "
           f"stored outputs in `realtest/outputs/{task_name}/{variant(shots)}/`.", ""]

    # 1. the models
    out += ["## The models", ""]
    rows = []
    for f, name in enumerate(names):
        rows.append([name, fmt_pct(correct[f][held_out].mean()), f"{costs[f]:.3f}", f"{costs[f] / costs[0]:.1f}x",
                     f"{auroc(signal[f][held_out], correct[f][held_out]):.2f}"])
    out += [table(["Model", "Accuracy alone", "Seconds per request", "Cost against the smallest",
                   "AUROC of the confidence signal"], rows), "",
            "Seconds per request are compute time reported by the server, with the instructions "
            "cached between requests.", ""]

    # 2. the lookup stage
    out += ["## The deterministic lookup stage", ""]
    out += ["It answers when the five closest past requests agree and the closest is similar enough. How much it "
            "answers, and how well, at different similarity thresholds, on the test half:", ""]
    rows = []
    for similarity in (0.3, 0.4, 0.5, 0.6, 0.7):
        f_test = fired_at(similarity)[held_out]
        accuracy = f"{100 * lookup_correct[held_out][f_test].mean():.1f}%" if f_test.any() else "n/a"
        rows.append([f"{similarity:.1f}", fmt_pct(f_test.mean()), accuracy])
    out += [table(["Similarity of at least", "Requests answered", "Accuracy on what it answers"], rows), "",
            f"Cost: {1000 * lookup_cost:.2f} ms per request, {lookup_cost / costs[0]:.4f} of the smallest model.", "",
            "Each design that uses the stage picks its similarity threshold on the calibration half, together with "
            "the confidence threshold, so that the whole cascade stays within the tolerance. The simulation "
            "assumed a stage 99.5% accurate, with a coverage chosen by hand.", ""]

    # 3. every design, against the largest model alone
    large = len(names) - 1
    out += [f"## Every design, against {names[large]} alone", ""]
    designs = []
    for size in range(1, len(names)):
        for smaller in itertools.combinations(range(large), size):
            designs.append(tuple(smaller) + (large,))
    rows, runs = [], {}
    for with_lookup in (False, True):
        for stages in ([(large,)] if with_lookup else []) + designs:
            run = evaluate(stages, with_lookup)
            runs[stages, with_lookup] = run
            label = (["lookup"] if with_lookup else []) + [names[f] for f in stages]
            delta = accuracy_delta(run, large)
            shares = [np.mean(run["where"] == j) for j in range(len(label))]
            lo, hi = saving_interval(run, large)
            rows.append((saving(run, large), [" > ".join(label),
                                             f"{fmt_pct(saving(run, large))} ({fmt_pct(lo)} to {fmt_pct(hi)})",
                                             fmt_points(*delta), " / ".join(fmt_pct(s) for s in shares)]))
    rows.sort(key=lambda r: -r[0])
    out += [table(["Design", "Compute saved", "Accuracy difference, points", "Share answered at each stage"],
                  [r[1] for r in rows]), ""]

    # 4. the 5x rule, triple by triple
    out += ["## The 5x rule on these models", "",
            "For each small, middle, large triple: what a third stage adds to the two-stage cascade, in points of "
            "saving against the large model of the triple. The step is the average cost ratio between neighbours.", ""]
    rows, verdicts = [], []
    for s, m, l in itertools.combinations(range(len(names)), 3):
        two, three = evaluate((s, l), False), evaluate((s, m, l), False)
        rules = evaluate((s, l), True)
        step = float(np.sqrt(costs[l] / costs[s]))
        gain_middle = saving_gain(three, two, l)
        gain_rules = saving_gain(rules, two, l)
        rows.append([f"{names[s]}, {names[m]}, {names[l]}", f"{step:.1f}x", fmt_pct(saving(two, l)),
                     fmt_points(*gain_middle), fmt_points(*gain_rules)])
        verdicts.append((step, gain_middle, gain_rules))
    out += [table(["Triple", "Step", "Two stages save", "Middle model adds", "Lookup stage adds"], rows), ""]

    below = [v for v in verdicts if v[0] < RULE_THRESHOLD]
    if below:
        middle_loses = sum(1 for _, g, _ in below if g[2] < 0)
        middle_wins = sum(1 for _, g, _ in below if g[1] > 0)
        rules_win = sum(1 for _, _, g in below if g[1] > 0)
        rules_lose = sum(1 for _, _, g in below if g[2] < 0)
        out += [f"Under 5x the rule predicts that a middle model does not pay and that a rule stage does. "
                f"Of {len(below)} triples under 5x:", "",
                f"- the middle model clearly gains in {middle_wins} and clearly loses in {middle_loses};",
                f"- the lookup stage clearly gains in {rules_win} and clearly loses in {rules_lose}.", "",
                "Clearly means that the whole 95% interval is on one side of zero.", ""]
    if len(below) < len(verdicts):
        out += [f"{len(verdicts) - len(below)} triples are at 5x or more; see the table for what the middle model "
                "adds there.", ""]
    else:
        out += ["No triple reaches 5x: this run says nothing about the upper branch of the rule.", ""]

    # 5. diagnostics
    out += ["## Diagnostics", "", "**Do the models fail on the same requests?** Correlation between their errors:", ""]
    errors = (~correct[:, held_out]).astype(float)
    corr = np.corrcoef(errors)
    out += [table([""] + names, [[names[i]] + [f"{corr[i, j]:.2f}" for j in range(len(names))]
                                 for i in range(len(names))]), "",
            "**Is the calibrated confidence honest?** Chi-square calibration test on the test half:", ""]
    rows = []
    for f, name in enumerate(names):
        check = calibration_chi2(confidence[f][held_out], correct[f][held_out])
        rows.append([name, f"{check['statistic']:.1f}", check["dof"], f"{check['p_value']:.3f}"])
    out += [table(["Model", "Chi-square", "Degrees of freedom", "p-value"], rows), "",
            "A small p-value means the declared confidence does not match the observed outcomes.", "",
            "## Limits of this run", "",
            "- One task, one model family, one machine. It is a first measurement, not a validation.",
            ("- The models see one or a few example requests per category; " if shots else
             "- The models classify without example requests; ")
            + f"the lookup stage uses all {len(train):,} labelled past requests.",
            "- Costs are measured with the instructions cached between requests, as a server would run it.",
            "- Thresholds are chosen on the calibration half. On the test half a design can end up more than "
            "half a point below the large model: check the accuracy column before comparing savings.",
            f"- With {n_test} test requests, differences of a few points are within noise: read the intervals.", ""]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", choices=sorted(data.SOURCES), default="banking77", help="which workload to analyse")
    parser.add_argument("--shots", type=int, default=DEFAULT_SHOTS, help="which prompt variant to analyse")
    parser.add_argument("--tolerance", type=float, default=0.005, help="accuracy allowed below the largest model")
    args = parser.parse_args()
    report = analyze(args.task, args.shots, args.tolerance)
    target = HERE / f"REPORT_{args.task}.md"
    target.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nwritten {target}")


if __name__ == "__main__":
    main()
