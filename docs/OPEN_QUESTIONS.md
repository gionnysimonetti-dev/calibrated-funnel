# Open questions

Problems where a contribution would change what this repository can claim.

1. **Does any of this hold on real models?** The whole repository is simulated. See the [real-model protocol](REAL_MODEL_PROTOCOL.md).
2. **When does a third stage pay off?** Simulations say: a middle model helps with a weak confidence signal and models far apart in cost; a rule stage helps when models are close in cost. Do the boundaries hold on real models, and can they be predicted from the four numbers measured up front?
3. **Why does moderate growth work?** Reduction coefficients growing by a factor of about 1.25 to 2 per stage are robust under noise. There is an intuitive explanation (early estimates are unreliable) but no derivation of the best growth rate from the noise level.
4. **A rule for the first cut.** The best first-stage cut depends on the reliability of the first evaluator. Is there a closed form?
5. **Correlated errors between models.** Models of the same family may fail on the same queries. How much does that reduce the saving, and does covariance weighting recover it?
6. **Memory.** A cascade keeps several models loaded. On a single GPU, when is loading a smaller model worth the memory it takes from the larger one?
7. **Recalibration policy.** The chi-square test says when calibration has drifted. How often should it run, and on how many outcomes, to catch drift without false alarms?
8. **Is there a link between the stages?** A quantity carried from one stage to the next that would fix the coefficients in advance, without tuning. None was found. Fixed evidence thresholds were tried in preliminary tests, not included in this repository, and did not help under a fixed budget.
9. **How good must a rule stage be?** The simulated rule stage is 99.5% accurate and fires only on easy queries. How quickly does its value fall as rules become less accurate or fire on hard queries?
10. **Measured use cases.** The workload profiles in `USE_CASES.md` are assumptions. Each one needs a real measurement: the four numbers and the saving actually obtained.
