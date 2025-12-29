import os
from typing import Optional

DEFAULT_MODEL_PATH = "model.joblib"

class FraudDetector:
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path or os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
        self.load_or_train_model()

    def load_or_train_model(self):
        import joblib

        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            # Train a dummy model
            print("Training dummy model...")
            # Deterministic training data for predictable behavior in tests.
            import numpy as np
            from sklearn.ensemble import IsolationForest

            rng = np.random.default_rng(42)
            X_train = rng.random((100, 1)) * 1000  # Random amounts
            self.model = IsolationForest(contamination=0.1, random_state=42)
            self.model.fit(X_train)
            joblib.dump(self.model, self.model_path)

    def predict(self, amount: float) -> bool:
        # Reshape for prediction
        prediction = self.model.predict([[amount]])
        # -1 is anomaly, 1 is normal
        return prediction[0] == -1
