import pandas as pd

import fetch
from fetch import plan_batches, returned_ids
from ids import ranked_base_games


def test_ranked_base_games_filters_and_sorts():
    ranks = pd.DataFrame({
        "id": [1, 2, 3, 4], "name": list("abcd"), "rank": [2, 0, 1, 3],
        "is_expansion": [0, 0, 0, 1], "bayesaverage": [7, 6, 8, 5], "usersrated": [10, 1, 20, 5],
    })
    assert ranked_base_games(ranks)["id"].tolist() == [3, 1]


def test_plan_batches_resumes_and_retries():
    ids = list(range(1, 46))
    manifest = [{"requested": list(range(1, 21)), "returned": list(range(1, 20))}]  # 20 was missing
    batches = plan_batches(ids, manifest, retry_missing=False)
    assert [len(b) for b in batches] == [20, 5] and batches[0][0] == 21
    retry = plan_batches(ids, manifest, retry_missing=True)
    assert retry[0][0] == 20


def test_returned_ids(sample_xml):
    assert returned_ids(sample_xml.read_bytes()) == [13, 999999, 926]


class FakeResponse:
    def __init__(self, status, content=b""):
        self.status_code, self.content, self.text, self.headers = status, content, "", {}


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)

    def get(self, *args, **kwargs):
        return self.responses.pop(0)


def test_get_batch_retries_queue_then_succeeds(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)
    session = FakeSession([FakeResponse(202), FakeResponse(429), FakeResponse(200, b"<items/>")])
    assert fetch.get_batch(session, [1, 2]) == b"<items/>"


def test_get_batch_unauthorized_is_fatal(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)
    session = FakeSession([FakeResponse(401)])
    try:
        fetch.get_batch(session, [1])
    except fetch.FatalFetchError:
        return
    raise AssertionError("expected FatalFetchError")
