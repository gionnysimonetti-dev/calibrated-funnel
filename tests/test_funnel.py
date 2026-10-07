import numpy as np

from funnel.confidence import (calibration_chi2, drift_chi2, inverse_covariance_weights,
                               measurement_covariance)
from funnel.routing import NEVER, BinnedCalibrator, RoutingWorld, evaluate, run_cascade, sample
from funnel.selection import geometric_schedule, multifidelity_cascade, staged_elimination


def test_drift_chi2_worked_example():
    out = drift_chi2([130, 110, 120, 40], [160, 100, 100, 40])
    assert abs(out["statistic"] - 10.625) < 1e-9
    assert out["dof"] == 3 and out["statistic"] > out["critical_5pct"]
    assert abs(out["shares"][0] - 0.5294) < 1e-3


def test_schedule_product_and_growth():
    etas = geometric_schedule(1000, 2, 3, 1.6)
    assert abs(np.prod(etas) - 500) < 1e-6
    assert abs(etas[1] / etas[0] - 1.6) < 1e-9
    assert geometric_schedule(1000, 2, 0) == []


def test_never_threshold_equals_largest_model():
    rng = np.random.default_rng(0)
    world = RoutingWorld()
    correct, signal = sample(world, 20_000, rng)
    conf = {f: np.zeros(20_000) for f in range(3)}
    acc, cost, shares = run_cascade(correct, conf, np.asarray(world.costs), (0, 1, 2), NEVER)
    assert acc == correct[2].mean()
    assert cost == sum(world.costs) and shares[-1] == 1.0


def test_calibrator_tracks_accuracy():
    rng = np.random.default_rng(1)
    correct, signal = sample(RoutingWorld(), 100_000, rng)
    conf = BinnedCalibrator(50).fit(signal[0], correct[0]).predict(signal[0])
    assert abs(conf.mean() - correct[0].mean()) < 1e-9
    assert calibration_chi2(conf, correct[0])["p_value"] > 0.01


def test_cascade_saves_when_most_queries_are_easy():
    out = evaluate(RoutingWorld(easy_fraction=0.9), n_calibration=60_000, n_test=60_000, seed=3)
    assert out["saving"] > 0.7 and out["accuracy_delta"] > -0.015


def test_staged_elimination_beats_uniform_allocation():
    flat = staged_elimination(300, 3.0, 16, [], n_trials=1500, rng=np.random.default_rng(4))
    staged = staged_elimination(300, 3.0, 16, geometric_schedule(300, 2, 3, 1.4), n_trials=1500,
                                rng=np.random.default_rng(4))
    assert staged > flat + 0.2


def test_multifidelity_respects_tiny_budget():
    p = multifidelity_cascade(200, (0.7, 0.85, 1.0), (1, 5, 25), [2, 2, 2, 2], geometric_schedule(200, 2, 3),
                              budget=0.1 * 200 * 25, n_trials=300, rng=np.random.default_rng(5))
    assert 0.0 <= p <= 0.2


def test_weights_without_correlation_favour_the_precise_measurement():
    w, var = inverse_covariance_weights((0.6, 0.8, 0.95), 0.0, (0.2, 0.2, 0.05))
    assert w[2] > w[1] > w[0] > 0 and 0 < var < 1
    total, err = measurement_covariance((0.6, 0.8, 0.95), 0.9, (0.2, 0.2, 0.05))
    assert np.all(np.linalg.eigvalsh(total) > 0) and np.all(np.linalg.eigvalsh(err) > 0)
    w_corr, _ = inverse_covariance_weights((0.6, 0.8, 0.95), 0.9, (0.2, 0.2, 0.05))
    assert w_corr[0] < 0


def test_rule_stage_answers_its_share_and_costs_little():
    from funnel.routing import RuleStage
    world = RoutingWorld(costs=(1.0, 3.0, 9.0), easy_fraction=0.7, signal_noise=1.5)
    rule = RuleStage(coverage=0.3)
    with_rule = evaluate(world, stages=(0, 2), n_calibration=80_000, n_test=80_000, seed=6, rule=rule)
    without = evaluate(world, stages=(0, 2), n_calibration=80_000, n_test=80_000, seed=6)
    assert abs(with_rule["stage_shares"][0] - 0.3) < 0.01
    assert abs(sum(with_rule["stage_shares"]) - 1.0) < 1e-9
    assert with_rule["saving"] > without["saving"]
    assert with_rule["accuracy_delta"] > -0.015


def test_planner_prefers_no_cascade_when_few_queries_are_easy():
    from funnel.planner import plan
    out = plan(easy=0.05, rules=0.0, costs=(1.0, 3.0, 9.0), signal="weak", n=60_000, seed=7)
    assert out["recommended"] == "large model only"
    out = plan(easy=0.9, rules=0.0, costs=(1.0, 8.0, 70.0), signal="good", n=60_000, seed=7)
    assert out["recommended"] == "small > large" and out["designs"][0]["saving"] > 0.8


def test_planner_accepts_a_medium_signal_and_ignores_the_cost_unit():
    from funnel.planner import plan
    base = plan(easy=0.6, rules=0.1, costs=(1.0, 3.0, 9.0), signal="medium", n=60_000, seed=7)
    scaled = plan(easy=0.6, rules=0.1, costs=(10.0, 30.0, 90.0), signal="medium", n=60_000, seed=7)
    assert base["recommended"] == scaled["recommended"]
    for a, b in zip(base["designs"], scaled["designs"]):
        assert a["design"] == b["design"] and abs(a["saving"] - b["saving"]) < 1e-9
