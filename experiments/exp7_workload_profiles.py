"""Experiment 7. Which design for which workload?

Question: for a few typical workloads, which cascade design saves the most compute at equal
accuracy, and how much does a deterministic first stage (rules, exact lookups) contribute?

The profiles are illustrative assumptions, not measurements. Replace them with your own
figures using `python -m funnel.planner`.
"""
from funnel.planner import plan

from .common import md_table, pct, seed_for, write_csv

PROFILES = (
    # name, share of easy queries, share answerable by rules, confidence signal
    ("Ticket triage into a fixed taxonomy", 0.8, 0.3, "good"),
    ("Catalogue or spare-part matching", 0.7, 0.5, "good"),
    ("Sales assistant turns", 0.6, 0.1, "weak"),
    ("Document field extraction", 0.5, 0.2, "weak"),
    ("Open-ended analysis", 0.1, 0.0, "weak"),
)
LADDERS = (("wide", (1.0, 8.0, 70.0)), ("narrow", (1.0, 3.0, 9.0)))
DESIGNS = ("small > large", "small > medium > large", "rules > large model only",
           "rules > small > large", "rules > small > medium > large")


def run() -> str:
    rows = []
    for name, easy, rules, signal in PROFILES:
        for ladder_name, costs in LADDERS:
            result = plan(easy, rules, costs, signal, seed=seed_for("exp7", name, ladder_name))
            by_design = {d["design"]: d["saving"] for d in result["designs"]}
            rows.append([name, easy, rules, signal, ladder_name, result["recommended"]] +
                        [round(by_design[d], 4) if d in by_design else "" for d in DESIGNS])
    write_csv("exp7_workload_profiles.csv",
              ["profile", "easy_fraction", "rule_coverage", "signal", "cost_ladder", "best_design"] +
              [f"saving: {d}" for d in DESIGNS], rows)

    def fmt(v):
        return pct(v) if v != "" else "n/a"

    parts = ["## Experiment 7. Which design for which workload?\n",
             "Illustrative workload profiles, not measurements. Saving versus the large model alone "
             "at equal accuracy. Rule stage: 99.5% accurate, cost 0.01. The recommended design is the "
             "simplest one within 2 points of the best: fewest models first, then no rule stage.\n"]
    for ladder_name, costs in LADDERS:
        parts.append(f"**{ladder_name.capitalize()} cost ladder ({' : '.join(f'{c:g}' for c in costs)})**\n")
        sub = [r for r in rows if r[4] == ladder_name]
        parts.append(md_table(["Workload (easy share, rule coverage, signal)", "Simplest near-best design"] + list(DESIGNS),
                              [[f"{r[0]} ({pct(r[1])}, {pct(r[2])}, {r[3]})", r[5]] + [fmt(v) for v in r[6:]]
                               for r in sub]) + "\n")
    return "\n".join(parts)


if __name__ == "__main__":
    print(run())
