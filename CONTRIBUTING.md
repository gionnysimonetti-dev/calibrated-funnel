# Contributing

Contributions are welcome, including ones that show the method failing.

## Most useful

1. **Run the real-model protocol** in `docs/REAL_MODEL_PROTOCOL.md` and share the stored outputs.
2. **Measure a use case**: the four numbers of a real workload (see `docs/USE_CASES.md`) and what the cascade saved.
3. **Find a counterexample**: a workload, a noise model or a cost structure where the rules in the README break.
4. **Point to prior work** missing from the related work section.
5. **Take an open question** from `docs/OPEN_QUESTIONS.md`.

## Ground rules

- Every number must be reproducible: fixed seed, script in `experiments/`, output in `results/`.
- Say whether a result is simulated or measured on real models.
- State limits next to results.
- Run `python -m pytest -q` before opening a pull request.

Open an issue first for anything larger than a small fix.
