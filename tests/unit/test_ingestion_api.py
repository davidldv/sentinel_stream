from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _add_ingestion_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "ingestion"))


class _KafkaStub:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    async def send_message(self, topic: str, message: dict):
        self.sent.append((topic, message))


def test_health_endpoint_without_kafka(monkeypatch: pytest.MonkeyPatch) -> None:
    _add_ingestion_to_path()

    import main as ingestion_main

    app = ingestion_main.create_app(enable_kafka=False)
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_transactions_endpoint_queues_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    _add_ingestion_to_path()

    import main as ingestion_main

    stub = _KafkaStub()
    monkeypatch.setattr(ingestion_main, "kafka_client", stub, raising=True)

    app = ingestion_main.create_app(enable_kafka=False)
    client = TestClient(app)

    payload = {
        "transaction_id": "tx_test",
        "user_id": "u_1",
        "amount": 123.45,
        "currency": "USD",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "merchant_id": "m_1",
        "location": "Test",
    }

    r = client.post("/transactions/", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "queued"

    assert len(stub.sent) == 1
    topic, msg = stub.sent[0]
    assert topic == "transactions"
    assert msg["transaction_id"] == "tx_test"
