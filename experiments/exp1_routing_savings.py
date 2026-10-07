"""Experiment 1. Compute saved by a confidence-gated cascade at equal accuracy.

Question: how much compute does the cascade save compared with always using the largest
model, when accuracy must stay within half a point? How does it depend on the share of
easy queries, on the quality of the confidence signal, and on using three stages or two?
"""
from funnel.routing import RoutingWorld, evaluate

from .common import md_table, pct, seed_for, write_csv

EASY = (0.0, 0.5, 0.7, 0.9)
SIGNALS = (("good", 0.5), ("weak", 1.5))
COSTS = ((1.0, 8.0, 70.0), (1.0, 5.0, 25.0))
DESIGNS = (("three stages", (0, 1, 2)), ("two stages", (0, 2)))


def run() -> str:
    rows = []
    for costs in COSTS:
        for easy in EASY:
            for label, noise in SIGNALS:
                world = RoutingWorld(costs=costs, easy_fraction=easy, signal_noise=noise)
                for design, stages in DESIGNS:
                    out = evaluate(world, stages=stages, seed=seed_for("exp1", costs, easy, noise))
                    rows.append([":".join(f"{c:g}" for c in costs), easy, label, design,
                                 out["threshold"] if out["threshold"] <= 1 else "never",
                                 round(out["saving"], 4), round(out["accuracy"], 4),
                                 round(out["big_accuracy"], 4), round(out["accuracy_delta"], 4),
                                 " / ".join(f"{s:.2f}" for s in out["stage_shares"])])
    header = ["costs", "easy_fraction", "signal", "design", "threshold", "saving",
              "accuracy", "big_model_accuracy", "accuracy_delta", "share_answered_per_stage"]
    write_csv("exp1_routing_savings.csv", header, rows)

    def cell(costs, easy, signal, design):
        r = next(r for r in rows if r[0] == costs and r[1] == easy and r[2] == signal and r[3] == design)
        return f"{pct(r[5])} ({100 * r[8]:+.1f})"

    parts = ["## Experiment 1. Compute saved at equal accuracy\n",
             "Saving versus the largest model alone. In brackets: accuracy difference in points "
             "on the test sample (the threshold was chosen on a separate calibration sample "
             "with a tolerance of 0.5 points). Negative saving means the cascade costs more.\n"]
    for costs in COSTS:
        key = ":".join(f"{c:g}" for c in costs)
        parts.append(f"**Relative costs {key.replace(':', ' : ')}**\n")
        table = [[pct(easy), cell(key, easy, "good", "three stages"), cell(key, easy, "good", "two stages"),
                  cell(key, easy, "weak", "three stages"), cell(key, easy, "weak", "two stages")]
                 for easy in EASY]
        parts.append(md_table(["Easy queries", "Good signal, 3 stages", "Good signal, 2 stages",
                               "Weak signal, 3 stages", "Weak signal, 2 stages"], table) + "\n")
    return "\n".join(parts)


if __name__ == "__main__":
    print(run())
