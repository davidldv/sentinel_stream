from __future__ import annotations

import sys
from pathlib import Path

import pytest


def _add_processing_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "processing"))


def test_fraud_detector_trains_and_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _add_processing_to_path()

    pytest.importorskip("sklearn")

    # Import after sys.path change
    from model import FraudDetector

    model_path = tmp_path / "model.joblib"
    monkeypatch.setenv("MODEL_PATH", str(model_path))

    detector1 = FraudDetector()
    assert detector1.model is not None
    assert model_path.exists()

    detector2 = FraudDetector()
    assert detector2.model is not None


def test_fraud_detector_predict_returns_bool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _add_processing_to_path()

    pytest.importorskip("sklearn")

    from model import FraudDetector

    model_path = tmp_path / "model.joblib"
    monkeypatch.setenv("MODEL_PATH", str(model_path))

    detector = FraudDetector()
    assert isinstance(detector.predict(10.0), bool)
    assert isinstance(detector.predict(10_000.0), bool)
