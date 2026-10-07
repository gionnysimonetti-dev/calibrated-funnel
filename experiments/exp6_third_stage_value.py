"""Experiment 6. When does a third stage pay off?

Question: published cascades mostly use two tiers. Under which conditions does adding a
middle model save compute at equal accuracy, and when does it cost more than it saves?
Also: what does this simulation predict at the cost ratio used in published two-tier studies?
"""
from funnel.routing import RoutingWorld, evaluate

from .common import md_table, pct, seed_for, write_csv

LADDERS = ((1.0, 1.7, 3.0), (1.0, 3.0, 9.0), (1.0, 5.0, 25.0), (1.0, 8.0, 70.0))
EASY = (0.5, 0.7, 0.9)
SIGNALS = (("good", 0.5), ("weak", 1.5))
PUBLISHED_RATIO = 2.7


def run() -> str:
    rows = []
    for ladder in LADDERS:
        for label, noise in SIGNALS:
            for easy in EASY:
                world = RoutingWorld(costs=ladder, easy_fraction=easy, signal_noise=noise)
                seed = seed_for("exp6", ladder, easy, noise)
                three = evaluate(world, stages=(0, 1, 2), seed=seed)["saving"]
                two = evaluate(world, stages=(0, 2), seed=seed)["saving"]
                rows.append([" : ".join(f"{c:g}" for c in ladder), label, easy,
                             round(three, 4), round(two, 4), round(three - two, 4)])
    write_csv("exp6a_third_stage_value.csv",
              ["costs", "signal", "easy_fraction", "saving_three_stages", "saving_two_stages", "difference"], rows)

    rows_b = []
    for label, noise in SIGNALS:
        for easy in EASY:
            world = RoutingWorld(abilities=(1.0, 2.4), costs=(1.0, PUBLISHED_RATIO), easy_fraction=easy,
                                 signal_noise=noise)
            out = evaluate(world, stages=(0, 1), seed=seed_for("exp6b", easy, noise))
            rows_b.append([label, easy, round(out["saving"], 4), round(out["stage_shares"][0], 4)])
    write_csv("exp6b_two_tier_published_ratio.csv", ["signal", "easy_fraction", "saving", "share_answered_by_small"], rows_b)

    def cell(ladder, signal, easy):
        r = next(r for r in rows if r[0] == ladder and r[1] == signal and r[2] == easy)
        return f"{100 * r[5]:+.0f} ({pct(r[3])} vs {pct(r[4])})"

    ladders = [" : ".join(f"{c:g}" for c in ladder) for ladder in LADDERS]
    parts = ["## Experiment 6. When does a third stage pay off?\n",
             "Points of compute saving gained (+) or lost (-) by adding the middle model, at equal "
             "accuracy. In brackets: saving with three stages versus two.\n"]
    for label, _ in SIGNALS:
        parts.append(f"**{label.capitalize()} confidence signal**\n")
        parts.append(md_table(["Model costs"] + [f"{pct(e)} easy queries" for e in EASY],
                              [[lad] + [cell(lad, label, e) for e in EASY] for lad in ladders]) + "\n")
    parts.append(f"**Two tiers at the cost ratio of published studies (1 : {PUBLISHED_RATIO:g})**\n")
    parts.append(md_table(["Signal"] + [f"{pct(e)} easy queries" for e in EASY],
                          [[label] + [pct(next(r for r in rows_b if r[0] == label and r[1] == e)[2]) for e in EASY]
                           for label, _ in SIGNALS]) + "\n")
    parts.append("For reference, two studies on real models report 31% and 43% cost reduction with two "
                 "tiers at cost ratios close to 3 (see Related work in the README).\n")
    return "\n".join(parts)


if __name__ == "__main__":
    print(run())
