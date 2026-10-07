"""Tests for the real-model test kit that need neither a model nor the dataset."""
import math

import numpy as np

from realtest.analyze import auroc, cascade, choose_threshold
from realtest.lookup import HistoryLookup, choose_similarity
from realtest.run_models import read_answer


def test_read_answer_parses_the_number_and_its_probability():
    response = {"response": " 23", "logprobs": [{"token": " ", "logprob": math.log(0.9)},
                                                {"token": "2", "logprob": math.log(0.8)},
                                                {"token": "3", "logprob": math.log(0.5)},
                                                {"token": ".", "logprob": math.log(0.1)}]}
    answer, confidence = read_answer(response, 77)
    assert answer == 22 and abs(confidence - 0.9 * 0.8 * 0.5) < 1e-9
    assert read_answer({"response": "no idea", "logprobs": []}, 77) == (-1, 0.0)
    assert read_answer({"response": "99", "logprobs": [{"token": "99", "logprob": 0.0}]}, 77) == (-1, 0.0)


def test_cascade_charges_only_the_stages_a_request_reaches():
    correct = np.array([[True, False, True, False], [True, True, True, True]])
    confidence = np.array([[0.9, 0.9, 0.2, 0.2], [1.0, 1.0, 1.0, 1.0]])
    costs = np.array([1.0, 10.0])
    ok, spent, where = cascade(correct, confidence, costs, (0, 1), 0.5)
    assert ok.tolist() == [True, False, True, True]
    assert spent.tolist() == [1.0, 1.0, 11.0, 11.0] and where.tolist() == [0, 0, 1, 1]
    fired = np.array([True, False, False, False])
    ok, spent, where = cascade(correct, confidence, costs, (0, 1), 0.5, rule=(0.01, fired, np.ones(4, bool)))
    assert spent[0] == 0.01 and where.tolist() == [0, 1, 2, 2]
    # the cheapest threshold that keeps every answer right is the one that escalates the wrong one
    assert choose_threshold(correct, confidence, costs, (0, 1), 1.0, [0.5, 0.95, 1.01]) == 0.95


def test_auroc_and_lookup_behave():
    assert auroc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([False, False, True, True])) == 1.0
    assert abs(auroc(np.array([0.5, 0.5, 0.5, 0.5]), np.array([False, True, False, True])) - 0.5) < 1e-9
    history = HistoryLookup(["my card has not arrived"] * 5 + ["what is the exchange rate"] * 5, [0] * 5 + [1] * 5)
    label, score, agree = history.query(["card has not arrived yet", "exchange rate today", "hello there"])
    assert label[:2].tolist() == [0, 1] and agree[:2].all() and score[2] == 0
    assert choose_similarity(np.full(40, 0.6), np.ones(40, bool), np.ones(40, bool)) == 0.3
    assert choose_similarity(np.full(40, 0.6), np.ones(40, bool), np.zeros(40, bool)) == 2.0
