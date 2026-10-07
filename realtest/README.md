# Real-model test

A first, minimal run of the [real-model protocol](../docs/REAL_MODEL_PROTOCOL.md), sized for an office PC with no graphics card.

**Status: the kit is ready, the models have not been run yet.** The only measured figure so far is the lookup stage, which needs no model.

## What it tests

The lower branch of the 5x rule: when neighbouring models are less than 5x apart in cost, a middle model should not pay and a deterministic stage should.

- **Workload.** [Banking77](https://github.com/PolyAI-LDN/task-specific-datasets): real customer requests to a bank, 77 categories. 3,080 test requests are the workload; 10,003 labelled training requests play the role of the ticket history. Licence CC BY 4.0.
- **Models.** Four sizes of one open family, served locally by [Ollama](https://ollama.com): `qwen2.5` at 0.5b, 1.5b, 3b and 7b. They classify without examples.
- **Confidence signal.** The probability the model gives to the tokens of its answer.
- **Cost.** Compute seconds per request, as measured by the server.
- **Deterministic stage.** A lookup in the history: it answers when the five closest past requests agree and the closest is similar enough. No model, about 0.3 ms per request.

## Run it

```bash
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b

python -m realtest.run_models     # runs every model on every request; a few hours on a CPU
python -m realtest.analyze        # seconds; writes realtest/REPORT.md
```

`run_models` can be stopped and restarted: stored requests are skipped. It prints the time left. For a shorter run on a fixed subset, add `--limit 1000`.

Python needs only numpy and scipy. The dataset is downloaded on first use into `realtest/data/`.

## What is stored

`realtest/outputs/<model>.jsonl`, one line per request: the answer, whether it is correct, the raw confidence, compute seconds. Every cascade design is then evaluated offline from these files, so no model has to run twice.

## How the result is read

The requests are split once, with a fixed seed, into a calibration half and a test half. Calibration, the confidence threshold and the similarity threshold of the lookup stage are all fitted on the calibration half. Every figure in the report comes from the test half, with 95% bootstrap intervals.

The report gives, for each small, middle, large triple of models: the measured cost step, what a middle model adds to the two-stage cascade, and what the lookup stage adds.

## The lookup stage alone

```bash
python -m realtest.lookup
```

On the test half it answers 28.6% of requests and is right on 99.5% of them. The simulation assumed a rule stage 99.5% accurate; here that figure is measured.

## Limits

- One task, one model family, one machine: a first measurement, not a validation.
- The four models span about one order of magnitude in cost, so no triple is likely to reach 5x. The upper branch of the rule needs a larger model.
- The models see no examples, while the lookup stage uses the labelled history. That is the situation of a team that has past tickets and no fine-tuned model.
