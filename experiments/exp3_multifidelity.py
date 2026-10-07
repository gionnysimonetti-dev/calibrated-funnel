"""Experiment 3. Cascade of evaluators: cheap and rough first, expensive and precise last.

Question: at equal cost, does a cascade of three evaluators beat using only the precise
one? How hard should the first stage cut, given how reliable its evaluator is?
"""
import math

from funnel.selection import geometric_schedule, multifidelity_cascade

from .common import md_table, pct, rng_for, write_csv

N = 1000
COSTS = (1.0, 5.0, 25.0)
TRIALS = 4000
BUDGETS = (0.25, 1.0, 2.0, 4.0)            # 1.0 = one precise evaluation of every candidate
CHEAP = (0.5, 0.7, 0.9)                    # reliability of the cheapest evaluator
CUTS = (1.5, 2, 3, 5, 8, 12, 20, 40)
CUT_RELIABILITY = (0.4, 0.6, 0.8, 0.95)


def reliabilities(r):
    return (r, (r + 1) / 2, 1.0)


def run() -> str:
    etas = geometric_schedule(N, 2, 3, 1.4)
    rows_a, rows_b = [], []
    for bm in BUDGETS:
        budget = bm * N * COSTS[2]
        common = dict(n_candidates=N, costs=COSTS, budget=budget, n_trials=TRIALS)
        flat = multifidelity_cascade(reliability=reliabilities(0.7), fidelities=[2], etas=[],
                                     rng=rng_for("exp3a", bm, "flat"), **common)
        precise = multifidelity_cascade(reliability=reliabilities(0.7), fidelities=[2, 2, 2, 2], etas=etas,
                                        rng=rng_for("exp3a", bm, "precise"), **common)
        row = [bm, round(flat, 4), round(precise, 4)]
        for r in CHEAP:
            row.append(round(multifidelity_cascade(reliability=reliabilities(r), fidelities=[0, 1, 2, 2],
                                                   etas=etas, rng=rng_for("exp3a", bm, r), **common), 4))
        rows_a.append(row)
    write_csv("exp3a_cascade_vs_precise.csv",
              ["budget", "precise_no_elimination", "precise_three_stages"] +
              [f"cascade_cheap_reliability_{r}" for r in CHEAP], rows_a)

    budget = 1.0 * N * COSTS[2]
    for r in CUT_RELIABILITY:
        for cut in CUTS:
            rest = math.sqrt((N / 2) / cut)
            if rest <= 1.02:
                continue
            p = multifidelity_cascade(N, reliabilities(r), COSTS, [0, 1, 2, 2], [cut, rest, rest], budget,
                                      n_trials=TRIALS, rng=rng_for("exp3b", r, cut))
            rows_b.append([r, cut, round(1 / cut, 4), round(p, 4)])
    write_csv("exp3b_first_stage_cut.csv", ["cheap_reliability", "first_coefficient", "share_kept", "p_best"], rows_b)

    def best_cut(r):
        sub = [x for x in rows_b if x[0] == r]
        top = max(sub, key=lambda x: x[3])
        worst = min(sub, key=lambda x: x[3])
        return [r, f"{top[1]:g}", pct(top[2]), pct(top[3]), pct(worst[3])]

    parts = ["## Experiment 3. Cascade of evaluators of different cost\n",
             f"{N} candidates, evaluator costs {' : '.join(f'{c:g}' for c in COSTS)}. Budget 1 = one "
             "precise evaluation of every candidate. Probability of picking the truly best candidate.\n",
             md_table(["Budget", "Precise only, no elimination", "Precise only, three stages"] +
                      [f"Cascade, cheap reliability {r}" for r in CHEAP],
                      [[f"{r[0]:g}"] + [pct(v) for v in r[1:]] for r in rows_a]) + "\n",
             "**How hard the first stage should cut** (budget 1, remaining reduction split equally "
             "between the other two stages)\n",
             md_table(["Cheap evaluator reliability", "Best first coefficient", "Share kept",
                       "Result with best cut", "Result with worst cut tried"],
                      [best_cut(r) for r in CUT_RELIABILITY]) + "\n"]
    return "\n".join(parts)


if __name__ == "__main__":
    print(run())
