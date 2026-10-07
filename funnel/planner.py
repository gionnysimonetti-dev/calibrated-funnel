"""What-if planner: which cascade design fits a given workload?

Given a workload profile (share of easy queries, how much a deterministic first stage can
answer, the cost ladder of the available models, the quality of the confidence signal),
compare the candidate designs and report the compute each saves at equal accuracy.

This is a what-if under the simulation's assumptions, not a prediction for a real system.
Use it to decide which designs are worth measuring.

Usage:
    python -m funnel.planner --easy 0.7 --rules 0.3 --costs 1 8 70 --signal weak
"""
from __future__ import annotations

import argparse

from .routing import RoutingWorld, RuleStage, evaluate

SIGNAL_NOISE = {"good": 0.5, "weak": 1.5}
MODEL_DESIGNS = (
    ("large model only", (2,)),
    ("small > large", (0, 2)),
    ("small > medium > large", (0, 1, 2)),
)
MIN_SAVING = 0.02   # below this, a cascade is not worth its complexity
NEAR_BEST = 0.02    # designs within this margin of the best are treated as equivalent


def plan(easy=0.7, rules=0.0, costs=(1.0, 8.0, 70.0), signal="good", rule_cost=0.01,
         rule_accuracy=0.995, tolerance=0.005, n=200_000, seed=0) -> dict:
    """Evaluate every design on the same simulated queries. Returns designs sorted by saving."""
    world = RoutingWorld(costs=tuple(costs), easy_fraction=easy, signal_noise=SIGNAL_NOISE[signal])
    rule = RuleStage(coverage=min(rules, easy), accuracy=rule_accuracy, cost=rule_cost) if rules > 0 else None
    designs = []
    for name, stages in MODEL_DESIGNS:
        for with_rule in ((False, True) if rule else (False,)):
            if not with_rule and len(stages) == 1:
                continue
            out = evaluate(world, stages=stages, n_calibration=n, n_test=n, tolerance=tolerance, seed=seed,
                           rule=rule if with_rule else None)
            designs.append({"design": ("rules > " if with_rule else "") + name,
                            "models": len(stages), "rule": with_rule,
                            "saving": out["saving"], "accuracy_delta": out["accuracy_delta"],
                            "threshold": out["threshold"], "stage_shares": out["stage_shares"]})
    designs.sort(key=lambda d: -d["saving"])
    best = designs[0]
    if best["saving"] < MIN_SAVING:
        return {"recommended": "large model only", "designs": designs}
    # among designs as good as the best, prefer the one with fewest models, then no rule stage
    equivalent = [d for d in designs if d["saving"] >= best["saving"] - NEAR_BEST]
    simplest = min(equivalent, key=lambda d: (d["models"], d["rule"], -d["saving"]))
    return {"recommended": simplest["design"], "designs": designs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--easy", type=float, default=0.7, help="share of easy queries (0-1)")
    parser.add_argument("--rules", type=float, default=0.0,
                        help="share of all queries a deterministic first stage can answer (0-1)")
    parser.add_argument("--costs", type=float, nargs=3, default=(1.0, 8.0, 70.0),
                        metavar=("SMALL", "MEDIUM", "LARGE"), help="relative compute per query")
    parser.add_argument("--signal", choices=sorted(SIGNAL_NOISE), default="good",
                        help="quality of the models' confidence signal")
    args = parser.parse_args()
    result = plan(args.easy, args.rules, args.costs, args.signal)
    print(f"{'design':38s} {'saving':>8s} {'accuracy':>10s}")
    for d in result["designs"]:
        print(f"{d['design']:38s} {100 * d['saving']:7.0f}% {100 * d['accuracy_delta']:+9.1f}")
    print(f"\nsimplest design within {100 * NEAR_BEST:.0f} points of the best: {result['recommended']}")
    print("saving: compute saved versus the large model alone; accuracy: difference in points")


if __name__ == "__main__":
    main()
