"""Step 1 of the real-model test: run every model once on every request and store everything.

Each model, served locally by Ollama, classifies each customer request into one of 77
categories. For every request the script stores the answer, whether it is correct, a raw
confidence signal (the probability the model gave to the tokens of its answer) and the
measured compute time. Nothing is decided here: every cascade design is evaluated later,
offline, from these stored outputs (see analyze.py).

The run can be interrupted and restarted: requests already stored are skipped.

Usage:
    python -m realtest.run_models
    python -m realtest.run_models --limit 1000          # a shorter run on a fixed subset
"""
from __future__ import annotations

import argparse
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
NUMBER = re.compile(r"\d+")


def system_prompt(categories) -> str:
    lines = [f"{i + 1}. {name.replace('_', ' ')}" for i, name in enumerate(categories)]
    return ("You classify customer requests sent to a bank. Reply with the number of the single "
            "best matching category from the list, and nothing else.\n\nCategories:\n" + "\n".join(lines))


def user_prompt(text: str) -> str:
    return f"Request: {text}\nCategory number:"


def call(host: str, path: str, payload: dict | None = None, timeout: float = 600.0) -> dict:
    request = urllib.request.Request(host + path, method="POST" if payload is not None else "GET",
                                     data=json.dumps(payload).encode() if payload is not None else None,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def read_answer(response: dict, n_categories: int):
    """Returns (category index or -1, confidence in 0..1).

    The confidence is the product of the probabilities of the tokens that make up the number
    the model answered: a raw signal, calibrated later on outcomes.
    """
    text = response.get("response", "")
    match = NUMBER.search(text)
    if not match:
        return -1, 0.0
    number = int(match.group())
    answer = number - 1 if 1 <= number <= n_categories else -1
    logprob, position = 0.0, 0
    for token in response.get("logprobs") or []:
        if position >= match.end():
            break
        logprob += float(token["logprob"])
        position += len(token["token"])
    return answer, (math.exp(logprob) if answer >= 0 else 0.0)


def classify(host: str, model: str, system: str, text: str) -> dict:
    return call(host, "/api/generate", {
        "model": model, "system": system, "prompt": user_prompt(text), "stream": False,
        "logprobs": True, "top_logprobs": 5, "keep_alive": "30m",
        "options": {"temperature": 0, "seed": 1, "num_predict": 6, "num_ctx": 2048},
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


def output_path(model: str) -> pathlib.Path:
    return OUTPUTS / (re.sub(r"[^A-Za-z0-9.]+", "_", model) + ".jsonl")


def run(models, limit, host) -> None:
    categories, _, test = data.load()
    items = data.select(len(test), limit)
    system = system_prompt(categories)
    check(host, models)
    OUTPUTS.mkdir(exist_ok=True)
    for model in models:
        path = output_path(model)
        done = set()
        if path.exists():
            done = {json.loads(line)["item"] for line in path.read_text(encoding="utf-8").splitlines() if line}
        todo = [int(i) for i in items if int(i) not in done]
        print(f"\n{model}: {len(done)} stored, {len(todo)} to run")
        if not todo:
            continue
        probe = classify(host, model, system, test[todo[0]][0])     # loads the model, fills the prompt cache
        if not probe.get("logprobs"):
            raise SystemExit("This Ollama version does not return token probabilities (logprobs). "
                             "Update Ollama to the latest version and run again.")
        started, correct = time.time(), 0
        with open(path, "a", encoding="utf-8") as out:
            for count, item in enumerate(todo, start=1):
                text, label = test[item]
                tick = time.time()
                response = classify(host, model, system, text)
                answer, confidence = read_answer(response, len(categories))
                correct += answer == label
                out.write(json.dumps({
                    "item": item, "model": model, "label": label, "answer": answer,
                    "correct": bool(answer == label), "confidence": confidence,
                    "response": response.get("response", ""),
                    "compute_seconds": (response.get("prompt_eval_duration", 0) + response.get("eval_duration", 0)) / 1e9,
                    "wall_seconds": time.time() - tick,
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "output_tokens": response.get("eval_count", 0),
                }) + "\n")
                out.flush()
                if count in (5, 25) or count % 100 == 0 or count == len(todo):
                    pace = (time.time() - started) / count
                    print(f"  {count}/{len(todo)}  accuracy so far {correct / count:.0%}  "
                          f"{pace:.2f}s per request  about {pace * (len(todo) - count) / 60:.0f} min left", flush=True)
    print("\nDone. Next: python -m realtest.analyze")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS), help="Ollama model names, any order")
    parser.add_argument("--limit", type=int, default=None, help="number of requests (default: all 3080 of the test set)")
    parser.add_argument("--host", default="http://localhost:11434")
    args = parser.parse_args()
    run(args.models, args.limit, args.host)


if __name__ == "__main__":
    main()
