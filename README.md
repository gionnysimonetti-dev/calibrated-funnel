# Calibrated Funnel Inference

**When is a third stage worth it?** A reproducible toolkit for planning model cascades on local hardware, one use case at a time.

In a cascade, a small model answers first and a query moves up to a larger model only when a calibrated confidence stays below a threshold. Published work shows this saves compute with two tiers. This repository asks the next practical question: for a given workload, should there be a third stage, and what should it be: a middle model, a deterministic rule stage, or nothing?

**Status: simulation only.** Every number here comes from synthetic data. No real model has been run yet. The protocol for real models is in [docs/REAL_MODEL_PROTOCOL.md](docs/REAL_MODEL_PROTOCOL.md), and help running it is welcome.

## The short answer (simulated)

| Situation | Third stage | Effect on compute saved |
| --- | --- | --- |
| Models far apart in cost (5x or more between neighbours), weak confidence signal, mostly easy queries | A middle model | +7 to +12 points |
| Models close in cost (about 3x between neighbours) | A deterministic rule stage, not a middle model | Rule stage +2 to +6 points; a middle model -4 to -10 |
| Models far apart in cost, good confidence signal | None | A third stage adds 2 points at most |
| Few easy queries | No cascade at all | The large model alone is as cheap or cheaper |

The saving itself is set by the workload, not by the method: the share of easy queries and the cost ratio between models decide most of it.

## Plan your own workload

```bash
python -m funnel.planner --easy 0.6 --rules 0.1 --costs 1 3 9 --signal weak
```

```
design                                   saving   accuracy
rules > small > large                       33%      -0.4
small > large                               28%      -0.3
rules > small > medium > large              26%      -0.4
small > medium > large                      21%      -0.3
rules > large model only                    10%      -0.0

simplest design within 2 points of the best: rules > small > large
```

`--easy` is the share of easy queries, `--rules` the share a deterministic first stage can answer outright, `--costs` the relative compute of the small, medium and large model, `--signal` the quality of the confidence signal. The output is a what-if under the simulation's assumptions: it tells which designs are worth measuring, not what a real system will save.

## Use cases

[docs/USE_CASES.md](docs/USE_CASES.md) covers where a cascade tends to fit and where it does not: ticket triage into a fixed taxonomy, catalogue and spare-part matching, sales and support assistant turns, document field extraction. For each: what the stages are in practice, where the outcome data for calibration comes from, what an error costs, and what to measure first.

## What this is, and what it is not

Confidence-gated cascades are not new, including with calibrated confidence and on locally served open models (see [Related work](#related-work)). This repository does not claim the idea. The method was reached independently and then checked against the literature.

What it adds:

- **A decision rule for the third stage**, by cost ladder, confidence quality and workload.
- **A deterministic rule stage as a first-class stage**: exact lookups and business rules answer what they can before any model runs.
- **A planner** that turns four measurable numbers into a shortlist of designs to test.
- **Continuous verification**: chi-square tests that say when calibration has drifted and when the mix of queries has changed.
- **Code that reproduces every figure** with one command, so the claims can be checked, broken or improved.

## The method in five steps

1. Three stages with different evaluators, from the cheapest to the most precise.
2. At each stage, a cut sized on how reliable that stage's evaluator is.
3. A final choice that combines the measurements using their covariance.
4. A chi-square statistic as a confidence level.
5. Calibration of that confidence on real outcomes, verified with another chi-square test.

Formulas and assumptions are in [docs/METHOD.md](docs/METHOD.md).

## Results (simulated)

Full tables are in [results/RESULTS.md](results/RESULTS.md); each has a CSV next to it.

### Compute saved at equal accuracy

Relative model costs 1 : 8 : 70. Accuracy is kept within half a point of the largest model alone. The threshold is chosen on a calibration sample and results are measured on a separate test sample of 300,000 queries.

| Easy queries | Good signal, 3 stages | Good signal, 2 stages | Weak signal, 3 stages | Weak signal, 2 stages |
| --- | --- | --- | --- | --- |
| 0% | 5% | 4% | -6% | 1% |
| 50% | 52% | 54% | 38% | 34% |
| 70% | 73% | 72% | 60% | 48% |
| 90% | 92% | 90% | 85% | 77% |

The saving is in compute, energy and latency, not memory: all models must stay loaded.

### The value of the middle model

Points of saving gained or lost by adding the middle model, with a weak confidence signal.

| Model costs | 50% easy queries | 70% easy queries | 90% easy queries |
| --- | --- | --- | --- |
| 1 : 1.7 : 3 | -21 | -16 | -3 |
| 1 : 3 : 9 | -10 | 0 | +3 |
| 1 : 5 : 25 | 0 | +12 | +7 |
| 1 : 8 : 70 | +5 | +12 | +9 |

With a good signal the middle model gains 2 points at most and loses up to 23 when costs are close.

### Sanity check against published results

At the cost ratio used in published two-tier studies (1 : 2.7), this simulation gives 12% to 55% saving with 70% to 90% easy queries. Two studies on real models report 31% and 43%. The simulation is in the same range, and does not claim better results.

### Staged elimination among noisy candidates

The same funnel logic applies to choosing the best of many candidates under a fixed evaluation budget: prompt variants, configurations, intervention scenarios. 1,000 candidates, 16 evaluations per candidate in total, probability of picking the truly best one.

| Design | Clean data | Noisy data |
| --- | --- | --- |
| No elimination | 61% | 21% |
| Three stages, equal coefficients | 95% | 68% |
| Three stages, coefficients growing 1.62x | 95% | 74% |
| Three stages, coefficients shrinking (0.62x) | 95% | 60% |
| Three stages, growing 1.4x, equal budget split | 96% | 71% |
| Three stages, growing 1.4x, first stage given 10% of the budget | 93% | 47% |

- Most of the gain comes from going from one stage to three. More than six stages makes things worse.
- With noisy data, cut lightly first and harder later.
- Do not starve the first stage.

### Cascade of evaluators of different cost

1,000 candidates, evaluator costs 1 : 5 : 25. Budget 1 equals one precise evaluation of every candidate.

| Budget | Precise evaluator only, three stages | Cascade cheap, medium, precise |
| --- | --- | --- |
| 0.25 | 6% | 37% |
| 1 | 21% | 69% |
| 2 | 45% | 77% |
| 4 | 87% | 82% |

On a tight budget the cascade wins by a wide margin. With a generous budget the precise evaluator alone catches up, because the cheap evaluator's systematic errors sometimes discard the best candidate for good. The more reliable the first evaluator, the harder it can cut: the best first-stage cut keeps 33% of candidates at reliability 0.4, 12% at 0.8 and 2% at 0.95.

### Combining measurements and trusting the result

- **Never average measurements of different quality.** A plain average of the three loses up to 20 points against using the last measurement alone. Inverse-covariance weighting gains 0.4 to 4 points.
- **A chi-square on the gap between the two leading candidates ranks cases well**: the choice is correct in 87% of the most confident fifth and 36% of the least confident fifth. Read directly, it is not a probability.
- **The posterior probability from the covariance model is calibrated**: declared and observed frequencies match band by band, and it passes the chi-square calibration test (7.5 on 9 bins, p = 0.59).

## What does not hold

Things tested that did not survive:

- A universal set of reduction coefficients. The best ones depend on the number of candidates and on the noise.
- A special role for prime numbers, Fibonacci numbers or other named sequences. A generic schedule growing 1.4x per stage matches or beats every named sequence tried (experiment 5).
- A third model as a general improvement. It helps in one corner of the space and hurts elsewhere (experiment 6).
- Fixed evidence thresholds in the style of a sequential probability ratio test. In preliminary tests, not included here, they did not beat fixed fractions under a fixed budget.

## Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q                 # about a second
python -m experiments.run_all       # about three minutes, rewrites results/
```

Seeds are fixed per experimental cell, so the output is identical on every run with the same library versions.

## Repository layout

```
funnel/routing.py       confidence-gated cascade of models, with an optional rule stage
funnel/planner.py       what-if planner for a workload profile
funnel/selection.py     staged elimination, single evaluator and cascade of evaluators
funnel/confidence.py    covariance weights, chi-square confidence, calibration and drift tests
experiments/            one script per experiment, plus run_all
results/                RESULTS.md and one CSV per table
docs/                   method, use cases, real-model protocol, open questions
tests/                  unit tests
```

## Limits

- **Synthetic data.** Difficulty, model ability and the confidence signal follow simple Gaussian assumptions. Real models may behave differently, in particular on how informative their confidence signal is.
- **Illustrative workload profiles.** The profiles in the use cases are assumptions, not measurements of real systems.
- **Assumed costs.** Cost ladders are inputs. Measure them on your own hardware.
- **Optimistic independence.** In the routing simulation each model's confidence noise is independent. Models of the same family may fail on the same queries.
- **An idealised rule stage.** It is assumed 99.5% accurate on what it answers and to fire only on easy queries.

## Related work

Model cascades and routing:

- Chen, Zaharia, Zou. [FrugalGPT](https://arxiv.org/abs/2305.05176), 2023.
- Kotte. [UCCI: Calibrated Uncertainty for Cost-Optimal LLM Cascade Routing](https://arxiv.org/abs/2605.18796), 2026. Two locally served models, isotonic calibration, 31% cost reduction.
- Dou, Lian, Li. [Conformal Cascade: Distribution-Free Accuracy Guarantees for Multi-Tier LLM Inference](https://arxiv.org/abs/2607.25018), 2026. Multi-tier framework with formal accuracy guarantees, evaluated with two tiers on open-weight models, 43% cost reduction.
- [CARGO: A Framework for Confidence-Aware Routing of Large Language Models](https://arxiv.org/abs/2509.14899), 2025.
- [Learning to Route LLMs with Confidence Tokens](https://arxiv.org/abs/2410.13284), 2024.
- [When Models Know When They Do Not Know: Calibration, Cascading, and Cleaning](https://arxiv.org/abs/2601.07965), 2026.
- AutoMix: Automatically Mixing Language Models, 2023.

Staged elimination under a fixed budget:

- Karnin, Koren, Somekh. [Almost Optimal Exploration in Multi-Armed Bandits](https://proceedings.mlr.press/v28/karnin13.pdf) (Sequential Halving), 2013.
- Jamieson, Talwalkar. [Non-stochastic Best Arm Identification and Hyperparameter Optimization](https://arxiv.org/abs/1502.07943), 2016.
- Shahrampour, Noshad, Tarokh. [On Sequential Elimination Algorithms for Best-Arm Identification in Multi-Armed Bandits](https://arxiv.org/abs/1609.02606), 2016.
- Li et al. [Hyperband](https://homes.cs.washington.edu/~jamieson/hyperband.html), 2018.
- Cochran. Improvement by means of selection, 1951.

Statistics:

- Guo et al. [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599), 2017.
- Hosmer, Lemeshow. Goodness-of-fit tests for the multiple logistic regression model, 1980.
- Wald. Sequential tests of statistical hypotheses, 1945.
- Mahalanobis. On the generalised distance in statistics, 1936.

The literature check is partial. Pointers to work this list misses are welcome.

## Contributing

The most useful contributions are a real-model run of the protocol and a measured use case: the four numbers of a real workload and what the cascade actually saved. Counterexamples are just as welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md).

## Use of AI

The simulation code and part of the statistical analysis were developed with an AI assistant (Claude, Anthropic). The author reviewed the design and takes responsibility for the content. All results can be regenerated from this repository.

## License and citation

Code under the MIT License. See [CITATION.cff](CITATION.cff) to cite this work.

Author: Giovanni Simonetti.
