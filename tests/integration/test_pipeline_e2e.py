from __future__ import annotations

import json
import time
from typing import Any

import pytest
import redis
import requests


@pytest.mark.integration
def test_end_to_end_pipeline_writes_result_to_redis() -> None:
    base_url = "http://localhost:8000"

    # Wait for ingestion API to be ready
    deadline = time.time() + 60
    while True:
        try:
            r = requests.get(f"{base_url}/health", timeout=2)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass

        if time.time() > deadline:
            raise AssertionError("Ingestion API did not become ready within 60s")
        time.sleep(1)

    rds = redis.Redis(host="localhost", port=6379, decode_responses=True)

    tx_id = f"tx_e2e_{int(time.time())}"

    # Clear prior state (best effort)
    rds.hdel("transaction_results", tx_id)

    payload: dict[str, Any] = {
        "transaction_id": tx_id,
        "user_id": "u_1",
        "amount": 10000.0,
        "currency": "USD",
        "timestamp": "2023-10-27T10:00:00",
        "merchant_id": "m_1",
        "location": "Unknown",
    }

    post = requests.post(f"{base_url}/transactions/", json=payload, timeout=5)
    assert post.status_code == 200
    assert post.json()["transaction_id"] == tx_id

    # Poll for processing decision
    deadline = time.time() + 60
    raw = None
    while time.time() < deadline:
        raw = rds.hget("transaction_results", tx_id)
        if raw:
            break
        time.sleep(1)

    assert raw is not None, "Processor did not write result to Redis within 60s"

    doc = json.loads(raw)
    assert "is_fraud" in doc
    assert isinstance(doc["is_fraud"], bool)
    assert doc["transaction"]["transaction_id"] == tx_id
