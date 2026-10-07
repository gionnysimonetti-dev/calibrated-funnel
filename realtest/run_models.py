"""Step 1 of the real-model test: run every model once on every request and store everything.

Each model, served locally by Ollama, classifies each customer request into one of 77
categories by answering with the category name. For every request the script stores the
answer, whether it is correct, a raw confidence signal (the probability the model gave to
the tokens of its answer) and the measured compute time. Nothing is decided here: every
cascade design is evaluated later, offline, from these stored outputs (see analyze.py).

The run can be interrupted and restarted: requests already stored are skipped.

Usage:
    python -m realtest.run_models
    python -m realtest.run_models --limit 100           # a short trial on a fixed subset
    python -m realtest.run_models --shots 0             # category names only, no example requests
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import pathlib
import re
import time
import urllib.error
import urllib.request

from . import data

OUTPUTS = pathlib.Path(__file__).resolve().parent / "outputs"
DEFAULT_MODELS = ("qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "qwen2.5:7b")
DEFAULT_SHOTS = 1


def variant(shots: int) -> str:
    """Name of the prompt variant; outputs of different variants are kept apart."""
    return f"names-{shots}shot"


def display(name: str) -> str:
    """Category name as shown to the model and as expected back: 'card_arrival' -> 'card arrival'."""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def pick_examples(train, n_categories: int, shots: int):
    """For each category, `shots` past requests chosen by a fixed rule: short, typical ones."""
    by_category = [[] for _ in range(n_categories)]
    for text, label in train:
        by_category[label].append(" ".join(text.replace('"', "'").split()))
    examples = []
    for texts in by_category:
        texts = sorted(set(texts), key=lambda t: (len(t), t))
        positions = [0.25] if shots == 1 else [0.2 + 0.4 * j / (shots - 1) for j in range(shots)]
        examples.append([texts[int(p * (len(texts) - 1))] for p in positions] if shots else [])
    return examples


def system_prompt(categories, examples) -> str:
    lines = []
    for name, shown in zip(categories, examples):
        lines.append(f"- {display(name)}" + (": " + " | ".join(f'"{t}"' for t in shown) if shown else ""))
    head = "Categories, each with example requests:" if examples and examples[0] else "Categories:"
    return ("You classify customer requests sent to a bank. Reply with the name of the single best matching "
            "category, exactly as written in the list, and nothing else.\n\n" + head + "\n" + "\n".join(lines))


def user_prompt(text: str) -> str:
    return f"Request: {text}\nCategory:"


def call(host: str, path: str, payload: dict | None = None, timeout: float = 1800.0) -> dict:
    request = urllib.request.Request(host + path, method="POST" if payload is not None else "GET",
                                     data=json.dumps(payload).encode() if payload is not None else None,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def match_category(text: str, names) -> int:
    """Index of the category the model named, or -1 if the answer names none of them."""
    answer = display(text.strip().splitlines()[0]) if text.strip() else ""
    if not answer:
        return -1
    if answer in names:
        return names.index(answer)
    complete = [n for n in names if answer.startswith(n)]       # the answer goes on after a full name
    if complete:
        return names.index(max(complete, key=len))
    cut_short = [n for n in names if n.startswith(answer)]      # the answer stops before the end of a name
    if len(cut_short) == 1:
        return names.index(cut_short[0])
    close = difflib.get_close_matches(answer, names, n=1, cutoff=0.85)
    return names.index(close[0]) if close else -1


def read_answer(response: dict, names):
    """Returns (category index or -1, confidence in 0..1, log probabilities of the answer's tokens).

    The confidence is the probability the model gave to its whole answer: the product of the
    probabilities of its tokens. It is a raw signal, calibrated later on outcomes.
    """
    answer = match_category(response.get("response", ""), names)
    logprobs = []
    for token in response.get("logprobs") or []:
        if "\n" in token["token"] and logprobs:
            break
        logprobs.append(round(float(token["logprob"]), 5))
    confidence = math.exp(sum(logprobs)) if answer >= 0 and logprobs else 0.0
    return answer, confidence, logprobs


def classify(host: str, model: str, system: str, text: str, context: int) -> dict:
    return call(host, "/api/generate", {
        "model": model, "system": system, "prompt": user_prompt(text), "stream": False,
        "logprobs": True, "top_logprobs": 3, "keep_alive": "30m",
        "options": {"temperature": 0, "seed": 1, "num_predict": 20, "num_ctx": context, "stop": ["\n"]},
    })


def check(host: str, models) -> None:
    try:
        version = call(host, "/api/version", timeout=10).get("version", "unknown")
    except (urllib.error.URLError, OSError) as error:
        raise SystemExit(f"Cannot reach Ollama at {host}. Start Ollama and try again. ({error})")
    installed = {m["name"] for m in call(host, "/api/tags", timeout=30).get("models", [])}
    missing = [m for m in models if m not in installed and m + ":latest" not in installed]
    if missing:
        raise SystemExit("Models not installed: " + ", ".join(missing) + ". Run: ollama pull <model>")
    print(f"Ollama {version}, models found: {', '.join(models)}")


def output_path(model: str, shots: int) -> pathlib.Path:
    return OUTPUTS / variant(shots) / (re.sub(r"[^A-Za-z0-9.]+", "_", model) + ".jsonl")


def run(models, limit, host, shots) -> None:
    categories, train, test = data.load()
    items = data.select(len(test), limit)
    names = [display(c) for c in categories]
    system = system_prompt(categories, pick_examples(train, len(categories), shots))
    context = next(size for size in (2048, 4096, 8192, 16384) if size >= len(system) / 3 + 400)
    check(host, models)
    print(f"prompt variant: {variant(shots)}, about {len(system) // 4} tokens of instructions, read once per model")
    for model in models:
        path = output_path(model, shots)
        path.parent.mkdir(parents=True, exist_ok=True)
        done = set()
        if path.exists():
            done = {json.loads(line)["item"] for line in path.read_text(encoding="utf-8").splitlines() if line}
        todo = [int(i) for i in items if int(i) not in done]
        print(f"\n{model}: {len(done)} stored, {len(todo)} to run")
        if not todo:
            continue
        print("  loading the model and reading the category list...", flush=True)
        probe = classify(host, model, system, test[todo[0]][0], context)     # also fills the prompt cache
        if not probe.get("logprobs"):
            raise SystemExit("This Ollama version does not return token probabilities (logprobs). "
                             "Update Ollama to the latest version and run again.")
        started, correct, unreadable, compute = time.time(), 0, 0, 0.0
        with open(path, "a", encoding="utf-8") as out:
            for count, item in enumerate(todo, start=1):
                text, label = test[item]
                tick = time.time()
                response = classify(host, model, system, text, context)
                answer, confidence, logprobs = read_answer(response, names)
                seconds = (response.get("prompt_eval_duration", 0) + response.get("eval_duration", 0)) / 1e9
                correct += answer == label
                unreadable += answer < 0
                compute += seconds
                out.write(json.dumps({
                    "item": item, "model": model, "shots": shots, "label": label, "answer": answer,
                    "correct": bool(answer == label), "confidence": confidence, "token_logprobs": logprobs,
                    "response": response.get("response", ""), "compute_seconds": seconds,
                    "wall_seconds": time.time() - tick,
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "output_tokens": response.get("eval_count", 0),
                }) + "\n")
                out.flush()
                if count in (5, 25) or count % 100 == 0 or count == len(todo):
                    pace = (time.time() - started) / count
                    print(f"  {count}/{len(todo)}  accuracy {correct / count:.0%}  unreadable answers {unreadable}  "
                          f"compute {compute / count:.2f}s per request  about {pace * (len(todo) - count) / 60:.0f} min left",
                          flush=True)
    print(f"\nDone. Next: python -m realtest.analyze --shots {shots}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS), help="Ollama model names, any order")
    parser.add_argument("--limit", type=int, default=None, help="number of requests (default: all 3080 of the test set)")
    parser.add_argument("--shots", type=int, default=DEFAULT_SHOTS,
                        help="example requests shown to the models for each category (default 1; 0 for none)")
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    run(args.models, args.limit, args.host, args.shots)


if __name__ == "__main__":
    main()
