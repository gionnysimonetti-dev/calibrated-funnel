"""Experiment 8. The 5x rule: which third stage, at which distance between models?

Question: experiment 6 shows that a middle model pays off only in one corner of the space.
Where exactly is the edge, and how does a deterministic rule stage compare with a middle
model as the third stage?

Cost ladders are 1 : r : r^2, so r is the cost ratio between neighbouring models. Every
figure is the saving of a three-stage design minus the saving of small > large on the same
simulated queries.
"""
from funnel.routing import RoutingWorld, RuleStage, evaluate

from .common import md_table, pct, seed_for, write_csv

RATIOS = (2, 3, 4, 5, 6, 8, 10)
EASY = (0.5, 0.6, 0.7, 0.8, 0.9)
EASY_RULES = (0.5, 0.7, 0.9)
SIGNALS = (("good", 0.5), ("medium", 1.0), ("weak", 1.5))
COVERAGE = (0.1, 0.3)
THRESHOLD = 5  # the rule of thumb under test


def run() -> str:
    middle, rules = {}, {}
    rows_a, rows_b = [], []
    for label, noise in SIGNALS:
        for r in RATIOS:
            for easy in EASY:
                world = RoutingWorld(costs=(1.0, float(r), float(r * r)), easy_fraction=easy, signal_noise=noise)
                seed = seed_for("exp8", r, easy, noise)
                two = evaluate(world, stages=(0, 2), seed=seed)["saving"]
                three = evaluate(world, stages=(0, 1, 2), seed=seed)["saving"]
                middle[label, r, easy] = three - two
                rows_a.append([label, r, easy, round(two, 4), round(three, 4), round(three - two, 4)])
                if easy not in EASY_RULES:
                    continue
                for coverage in COVERAGE:
                    with_rules = evaluate(world, stages=(0, 2), seed=seed, rule=RuleStage(coverage=coverage))["saving"]
                    rules[label, coverage, r, easy] = with_rules - two
                    rows_b.append([label, coverage, r, easy, round(two, 4), round(with_rules, 4),
                                   round(with_rules - two, 4), round(three - two, 4)])
    write_csv("exp8a_middle_model_by_ratio.csv",
              ["signal", "ratio_between_neighbours", "easy_fraction", "saving_two_models", "saving_three_models",
               "gain_middle_model"], rows_a)
    write_csv("exp8b_rules_vs_middle_model.csv",
              ["signal", "rule_coverage", "ratio_between_neighbours", "easy_fraction", "saving_two_models",
               "saving_rules_two_models", "gain_rule_stage", "gain_middle_model"], rows_b)

    def span(values):
        values = [round(100 * v) for v in values]
        return f"{min(values):+d} to {max(values):+d}"

    parts = ["## Experiment 8. The 5x rule: which third stage, at which distance between models?\n",
             "Cost ladders 1 : r : r^2, where r is the cost ratio between neighbouring models. Points of "
             "compute saving gained (+) or lost (-) against small > large, at equal accuracy.\n",
             "**Adding a middle model**\n"]
    for label, _ in SIGNALS:
        parts.append(f"{label.capitalize()} confidence signal:\n")
        parts.append(md_table(["Ratio between neighbours"] + [f"{pct(e)} easy queries" for e in EASY],
                              [[f"{r}x"] + [f"{100 * middle[label, r, e]:+.0f}" for e in EASY] for r in RATIOS]) + "\n")
    parts.append("**Adding a rule stage instead** (rule stage / middle model, same queries)\n")
    for label, _ in SIGNALS:
        for coverage in COVERAGE:
            parts.append(f"{label.capitalize()} confidence signal, rules answer {pct(coverage)} of queries:\n")
            parts.append(md_table(
                ["Ratio between neighbours"] + [f"{pct(e)} easy queries" for e in EASY_RULES],
                [[f"{r}x"] + [f"{100 * rules[label, coverage, r, e]:+.0f} / {100 * middle[label, r, e]:+.0f}"
                              for e in EASY_RULES] for r in RATIOS]) + "\n")

    below = [r for r in RATIOS if r < THRESHOLD]
    above = [r for r in RATIOS if r >= THRESHOLD]
    clear = ("good", "medium")
    summary = [
        ["Rule stage", span(v for (s, c, r, e), v in rules.items() if r in below),
         span(v for (s, c, r, e), v in rules.items() if r in above)],
        ["Middle model, weak signal", span(v for (s, r, e), v in middle.items() if s == "weak" and r in below),
         span(v for (s, r, e), v in middle.items() if s == "weak" and r in above)],
        ["Middle model, good or medium signal", span(v for (s, r, e), v in middle.items() if s in clear and r in below),
         span(v for (s, r, e), v in middle.items() if s in clear and r in above)],
    ]
    parts.append(f"**Summary: range of the gain below and from {THRESHOLD}x**\n")
    parts.append(md_table(["Third stage", f"Below {THRESHOLD}x", f"{THRESHOLD}x or more"], summary) + "\n")
    wins = sum(1 for (s, r, e), v in middle.items() if r in below and v >= 0.005)
    total = sum(1 for (s, r, e) in middle if r in below)
    parts.append(f"Below {THRESHOLD}x the middle model gains half a point or more in {wins} of {total} cells. "
                 "The rule stage is idealised: 99.5% accurate on what it answers, firing only on easy queries.\n")
    return "\n".join(parts)


if __name__ == "__main__":
    print(run())
