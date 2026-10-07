"""Experiment 2. Staged elimination: how many stages, which coefficients, which budget split.

Question: with a fixed evaluation budget, how often does staged elimination find the best
of N noisy candidates, and which design choices matter?
"""
from funnel.selection import geometric_schedule, staged_elimination

from .common import md_table, pct, rng_for, write_csv

BUDGET = 16          # evaluations per candidate, in total
FINALISTS = 2
CASES = ((100, 1.0), (100, 3.0), (1000, 1.0), (1000, 3.0))   # (candidates, noise sd)
STAGES = (0, 1, 2, 3, 4, 5, 6, 8)
GROWTH = (0.62, 1.0, 1.25, 1.62, 2.0, 2.5)
SPLITS = (("equal", (0.25, 0.25, 0.25, 0.25)), ("first stage heavy", (0.4, 0.2, 0.2, 0.2)),
          ("first stage starved", (0.1, 0.1, 0.4, 0.4)))


def trials(n):
    return 6000


def label(n, sigma):
    return f"{n} candidates, {'clean' if sigma == 1.0 else 'noisy'} data"


def run() -> str:
    rows_a, rows_b, rows_c = [], [], []
    for n, sigma in CASES:
        for s in STAGES:
            try:
                etas = geometric_schedule(n, FINALISTS, s, 1.0)
            except ValueError:
                continue
            p = staged_elimination(n, sigma, BUDGET, etas, n_trials=trials(n), rng=rng_for("exp2a", n, sigma, s))
            rows_a.append([n, sigma, s, round(p, 4)])
        for g in GROWTH:
            try:
                etas = geometric_schedule(n, FINALISTS, 3, g)
            except ValueError:
                continue
            p = staged_elimination(n, sigma, BUDGET, etas, n_trials=trials(n), rng=rng_for("exp2b", n, sigma, g))
            rows_b.append([n, sigma, g, " / ".join(f"{e:.1f}" for e in etas), round(p, 4)])
        etas = geometric_schedule(n, FINALISTS, 3, 1.4)
        for name, split in SPLITS:
            p = staged_elimination(n, sigma, BUDGET, etas, shares=list(split), n_trials=trials(n),
                                   rng=rng_for("exp2c", n, sigma, name))
            rows_c.append([n, sigma, name, round(p, 4)])
    write_csv("exp2a_number_of_stages.csv", ["candidates", "noise_sd", "stages", "p_best"], rows_a)
    write_csv("exp2b_growth_ratio.csv", ["candidates", "noise_sd", "growth", "coefficients", "p_best"], rows_b)
    write_csv("exp2c_budget_split.csv", ["candidates", "noise_sd", "split", "p_best"], rows_c)

    def a(n, sigma, s):
        hit = [r for r in rows_a if r[:3] == [n, sigma, s]]
        return pct(hit[0][3]) if hit else "n/a"

    def b(n, sigma, g):
        hit = [r for r in rows_b if r[:3] == [n, sigma, g]]
        return pct(hit[0][4]) if hit else "n/a"

    def c(n, sigma, name):
        return pct(next(r for r in rows_c if r[:3] == [n, sigma, name])[3])

    parts = ["## Experiment 2. Staged elimination among noisy candidates\n",
             f"Probability of picking the truly best candidate. Budget: {BUDGET} evaluations per "
             f"candidate in total, {FINALISTS} finalists.\n",
             "**Number of elimination stages** (equal coefficients; 0 = no elimination)\n",
             md_table(["Stages"] + [label(n, s) for n, s in CASES],
                      [[s] + [a(n, sg, s) for n, sg in CASES] for s in STAGES]) + "\n",
             "**Growth ratio between consecutive coefficients** (three stages, same overall reduction)\n",
             md_table(["Growth ratio"] + [label(n, s) for n, s in CASES],
                      [[g] + [b(n, sg, g) for n, sg in CASES] for g in GROWTH]) + "\n",
             "**Budget split across the three stages and the final choice** (growth ratio 1.4)\n",
             md_table(["Split"] + [label(n, s) for n, s in CASES],
                      [[f"{name} ({' / '.join(f'{int(100 * x)}%' for x in split)})"] +
                       [c(n, sg, name) for n, sg in CASES] for name, split in SPLITS]) + "\n"]
    return "\n".join(parts)


if __name__ == "__main__":
    print(run())
