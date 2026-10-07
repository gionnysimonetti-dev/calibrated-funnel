"""A deterministic first stage: look the request up in the labelled history.

No model runs here. Each request is compared with every past request by TF-IDF cosine
similarity over words and word pairs. If the five closest past requests all belong to the
same category and the closest one is similar enough, the stage answers with that category;
otherwise it passes the request on.

Unlike the rule stage of the simulation, nothing here is idealised: its coverage and its
accuracy are whatever the data give, and it can fire on hard requests.
"""
from __future__ import annotations

import re

import numpy as np
from scipy import sparse

TOKEN = re.compile(r"[a-z0-9]+")


def _terms(text: str):
    words = TOKEN.findall(text.lower())
    return words + [a + " " + b for a, b in zip(words, words[1:])]


class HistoryLookup:
    def __init__(self, texts, labels):
        docs = [_terms(t) for t in texts]
        self.vocabulary = {}
        for doc in docs:
            for term in doc:
                self.vocabulary.setdefault(term, len(self.vocabulary))
        counts = self._matrix(docs)
        df = np.asarray((counts > 0).sum(axis=0)).ravel()
        self.idf = np.log((1 + len(docs)) / (1 + df)) + 1.0
        self.history = self._normalise(counts.multiply(self.idf).tocsr())
        self.labels = np.asarray(labels)

    def _matrix(self, docs):
        rows, cols = [], []
        for i, doc in enumerate(docs):
            for term in doc:
                j = self.vocabulary.get(term)
                if j is not None:
                    rows.append(i)
                    cols.append(j)
        data = np.ones(len(rows))
        return sparse.csr_matrix((data, (rows, cols)), shape=(len(docs), len(self.vocabulary)))

    @staticmethod
    def _normalise(matrix):
        norms = np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=1)).ravel())
        norms[norms == 0] = 1.0
        return sparse.diags(1.0 / norms) @ matrix

    def query(self, texts, k: int = 5, chunk: int = 500):
        """For each request: (category of the closest past request, its cosine similarity,
        whether the k closest past requests all share that category)."""
        q = self._normalise(self._matrix([_terms(t) for t in texts]).multiply(self.idf).tocsr())
        label, score, agree = [], [], []
        for start in range(0, q.shape[0], chunk):
            sims = (q[start:start + chunk] @ self.history.T).toarray()
            top = np.argpartition(-sims, k - 1, axis=1)[:, :k]
            top_sims = np.take_along_axis(sims, top, axis=1)
            first = np.take_along_axis(top, top_sims.argmax(axis=1)[:, None], axis=1).ravel()
            labels = self.labels[top]
            label.append(self.labels[first])
            score.append(top_sims.max(axis=1))
            agree.append((labels == self.labels[first][:, None]).all(axis=1))
        return np.concatenate(label), np.concatenate(score), np.concatenate(agree)


def choose_similarity(score, agree, correct, min_accuracy: float = 0.99, grid=None) -> float:
    """The lowest similarity threshold at which the stage is at least `min_accuracy` correct.

    The stage fires when the k closest past requests agree and the closest one is at least
    this similar. Chosen on the calibration half only. Returns 2.0 (never fire) if no
    threshold qualifies.
    """
    grid = np.round(np.arange(0.30, 0.9001, 0.05), 2) if grid is None else grid
    for threshold in grid:
        fired = agree & (score >= threshold)
        if fired.sum() >= 30 and correct[fired].mean() >= min_accuracy:
            return float(threshold)
    return 2.0


def main() -> None:
    """Measure the lookup stage alone on the whole test set. Needs no model."""
    from . import data

    _, train, test = data.load()
    history = HistoryLookup([t for t, _ in train], [y for _, y in train])
    guess, score, agree = history.query([t for t, _ in test])
    correct = guess == np.array([y for _, y in test])
    calibration = data.split(len(test))
    threshold = choose_similarity(score[calibration], agree[calibration], correct[calibration])
    fired = agree & (score >= threshold)
    for name, half in (("calibration half", calibration), ("test half", ~calibration)):
        print(f"{name}: answers {fired[half].mean():.1%} of requests, {correct[half][fired[half]].mean():.1%} correct")
    print(f"similarity threshold {threshold:.2f}, chosen on the calibration half")


if __name__ == "__main__":
    main()
