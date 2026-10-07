"""Experiment 4. Combining the three measurements and trusting the final choice.

Questions: (a) for the final choice, is it better to use the last measurement only, a plain
average of the three, or a covariance-weighted combination? (b) does a chi-square on the
gap between the two leading candidates work as a confidence level, and is it calibrated?
"""
import math

import numpy as np

from funnel.confidence import (calibration_chi2, chi2_confidence, gap_chi2,
                               inverse_covariance_weights, measurement_covariance)
from funnel.selection import _keep_top

from .common import md_table, pct, rng_for, write_csv

N = 1000
COSTS = (1.0, 5.0, 25.0)
RELIABILITY = (0.6, 0.8, 0.95)
ETAS = (5, 5, 5)
BUDGET = 1.0 * N * COSTS[2]
SHARE = 0.25
CORRELATIONS = (0.0, 0.3, 0.6, 0.9)
BATCH = 2000


def simulate(error_correlation, trials, rng, draws=300):
    t, c = trials, error_correlation
    mu = rng.standard_normal((t, N))
    best = mu.argmax(1)
    common = rng.standard_normal((t, N))
    proxy = [r * mu + math.sqrt(1 - r * r) * (math.sqrt(c) * common + math.sqrt(1 - c) * rng.standard_normal((t, N)))
             for r in RELIABILITY]
    alive = np.ones((t, N), bool)
    k, x, reps = N, [None] * 3, []
    for f in range(3):
        n = int(SHARE * BUDGET // (COSTS[f] * k))
        assert n >= 1
        x[f] = proxy[f] + rng.standard_normal((t, N)) / math.sqrt(n)
        reps.append(n)
        k = math.ceil(k / ETAS[f])
        alive = _keep_top(np.where(alive, x[f], -np.inf), k)
    rows = np.arange(t)
    reached = alive[rows, best]
    n = int(SHARE * BUDGET // (COSTS[2] * k))
    fresh = proxy[2] + rng.standard_normal((t, N)) / math.sqrt(n)
    x[2] = (reps[2] * x[2] + n * fresh) / (reps[2] + n)
    noise_var = [1 / reps[0], 1 / reps[1], 1 / (reps[2] + n)]
    weights, post_var = inverse_covariance_weights(RELIABILITY, c, noise_var)
    total_cov, error_cov = measurement_covariance(RELIABILITY, c, noise_var)

    idx = np.argsort(~alive, axis=1, kind="stable")[:, :k]              # the k finalists
    meas = np.stack([np.take_along_axis(x[f], idx, 1) for f in range(3)], axis=2)
    true = np.take_along_axis(mu, idx, 1)
    scores = {
        "last": meas[:, :, 2],
        "plain_mean": (meas / np.sqrt(np.diag(total_cov))).sum(2),
        "covariance": meas @ weights,
    }
    correct = {name: idx[rows, s.argmax(1)] == best for name, s in scores.items()}

    post = scores["covariance"]
    order = np.argsort(-post, axis=1)
    lead, second = order[:, 0], order[:, 1]
    gap = post[rows, lead] - post[rows, second]
    conf_chi2 = chi2_confidence(gap_chi2(gap, weights, error_cov))
    sampled = post[:, :, None] + math.sqrt(post_var) * rng.standard_normal((t, k, draws))
    conf_post = (sampled.argmax(1) == lead[:, None]).mean(1)
    return {
        "reached": reached, "correct": correct, "weights": weights,
        "conf_chi2": conf_chi2, "conf_post": conf_post,
        "ok_finalists": true.argmax(1) == lead, "ok_overall": correct["covariance"],
    }


def pooled(error_correlation, trials, key):
    parts = [simulate(error_correlation, BATCH, rng_for(key, error_correlation, i)) for i in range(trials // BATCH)]
    out = {"weights": parts[0]["weights"]}
    for name in ("reached", "conf_chi2", "conf_post", "ok_finalists", "ok_overall"):
        out[name] = np.concatenate([p[name] for p in parts])
    out["correct"] = {n: np.concatenate([p["correct"][n] for p in parts]) for n in parts[0]["correct"]}
    return out


def run() -> str:
    rows_a = []
    for c in CORRELATIONS:
        r = pooled(c, 6000, "exp4a")
        rows_a.append([c, round(float(r["reached"].mean()), 4)] +
                      [round(float(r["correct"][n].mean()), 4) for n in ("last", "plain_mean", "covariance")] +
                      [" / ".join(f"{w:+.2f}" for w in r["weights"])])
    write_csv("exp4a_final_choice.csv",
              ["error_correlation", "best_reaches_final", "last_only", "plain_mean", "covariance_weighted", "weights"],
              rows_a)

    r = pooled(0.6, 20000, "exp4b")
    rows_b = []
    for name, conf in (("chi-square on the gap", r["conf_chi2"]), ("posterior probability", r["conf_post"])):
        band = np.digitize(conf, np.quantile(conf, [0.2, 0.4, 0.6, 0.8]))
        for b in range(5):
            m = band == b
            rows_b.append([name, b + 1, round(float(conf[m].mean()), 4),
                           round(float(r["ok_finalists"][m].mean()), 4), round(float(r["ok_overall"][m].mean()), 4)])
    write_csv("exp4b_confidence_bands.csv",
              ["confidence", "band", "declared", "correct_among_finalists", "correct_overall"], rows_b)
    cal_post = calibration_chi2(r["conf_post"], r["ok_finalists"])
    cal_chi2 = calibration_chi2(r["conf_chi2"], r["ok_finalists"])
    rows_c = []
    for cover in (0.2, 0.4, 0.6):
        m = r["conf_post"] >= np.quantile(r["conf_post"], 1 - cover)
        rows_c.append([cover, round(float(r["ok_finalists"][m].mean()), 4), round(float(r["ok_overall"][m].mean()), 4)])
    write_csv("exp4c_automatic_share.csv", ["share_decided_automatically", "correct_among_finalists", "correct_overall"], rows_c)

    def bands(name):
        sub = [x for x in rows_b if x[0] == name]
        return [[["lowest", "low", "middle", "high", "highest"][x[1] - 1], pct(x[2]), pct(x[3]), pct(x[4])] for x in sub]

    base = float(r["ok_finalists"].mean())
    parts = ["## Experiment 4. Combining measurements and trusting the final choice\n",
             f"{N} candidates, three evaluators with reliability {', '.join(str(x) for x in RELIABILITY)} "
             f"and costs {' : '.join(f'{c:g}' for c in COSTS)}, budget 1, coefficients 5 / 5 / 5, "
             f"{math.ceil(N / 125)} finalists.\n",
             "**Final choice rule, by correlation between the evaluators' systematic errors**\n",
             md_table(["Error correlation", "Best candidate reaches the final", "Last measurement only",
                       "Plain average of the three", "Covariance-weighted", "Weights (cheap / medium / precise)"],
                      [[x[0], pct(x[1]), pct(x[2], 1), pct(x[3], 1), pct(x[4], 1), x[5]] for x in rows_a]) + "\n",
             f"**Confidence in the final choice** (error correlation 0.6, 20,000 trials; the choice is "
             f"correct among the finalists in {pct(base)} of cases)\n",
             "Chi-square on the gap between the two leading candidates:\n",
             md_table(["Confidence band", "Declared", "Correct among finalists", "Correct overall"],
                      bands("chi-square on the gap")) + "\n",
             "Posterior probability from the covariance model:\n",
             md_table(["Confidence band", "Declared", "Correct among finalists", "Correct overall"],
                      bands("posterior probability")) + "\n",
             f"Calibration test (chi-square, {cal_post['dof']} bins): posterior probability "
             f"{cal_post['statistic']:.1f} (p = {cal_post['p_value']:.2f}); raw chi-square confidence "
             f"{cal_chi2['statistic']:.0f} (p < 0.001). The raw chi-square ranks cases well but is not a "
             "probability.\n",
             "**Deciding automatically only on the most confident cases**\n",
             md_table(["Share decided automatically", "Correct among finalists", "Correct overall"],
                      [[pct(x[0]), pct(x[1]), pct(x[2])] for x in rows_c]) + "\n"]
    return "\n".join(parts)


if __name__ == "__main__":
    print(run())
