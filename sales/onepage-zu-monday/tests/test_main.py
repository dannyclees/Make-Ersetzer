import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[2])]

import main  # noqa: E402
from test_flow import FIELD_LIST_PAYLOAD, FakeDrive, FakeMonday  # noqa: E402


def _client(monkeypatch, monday=None):
    monkeypatch.setenv("ONEPAGE_WEBHOOK_TOKEN", "geheim")
    monkeypatch.delenv("DEADLETTER_BUCKET", raising=False)
    monkeypatch.setattr(main, "_get_clients", lambda: (monday or FakeMonday(), FakeDrive()))
    return main.app.test_client()


def test_rejects_wrong_token(monkeypatch):
    assert _client(monkeypatch).post("/webhook?token=falsch", json=FIELD_LIST_PAYLOAD).status_code == 401


def test_accepts_token_and_creates(monkeypatch):
    resp = _client(monkeypatch).post("/webhook?token=geheim", json=FIELD_LIST_PAYLOAD)
    assert resp.status_code == 200 and resp.get_json()["status"] == "created"


def test_unroutable_is_200(monkeypatch):
    resp = _client(monkeypatch).post("/webhook", json={"secretkey": "geheim", "x": "y"})
    assert resp.status_code == 200 and resp.get_json()["status"] == "unroutable"


def test_api_failure_is_500(monkeypatch):
    class Broken(FakeMonday):
        def find_items(self, *a):
            raise RuntimeError("monday down")

    resp = _client(monkeypatch, Broken()).post("/webhook?token=geheim", json=FIELD_LIST_PAYLOAD)
    assert resp.status_code == 500
