"""
Multi-Layer Perceptron (MLP) Neural Network Model for GeoAI Spatial Matching.

Part of BhuDrishti SIH26013 GeoAI Engine.
Evaluates 7-dimensional spatial-attribute feature vectors using an MLPClassifier
with softmax probability outputs and deterministic fallback calibration.
"""

from __future__ import annotations

import numpy as np
from sklearn.neural_network import MLPClassifier


class SpatialMLPModel:
    """Wrapper around scikit-learn MLPClassifier for parcel match scoring."""

    def __init__(self) -> None:
        self.model = MLPClassifier(
            hidden_layer_sizes=(32, 16),
            activation="relu",
            solver="adam",
            max_iter=500,
            random_state=42,
        )
        self._is_trained = False
        self._calibrate()

    def _calibrate(self) -> None:
        """Calibrate the MLP network on a synthetic dataset of spatial feature vectors."""
        np.random.seed(42)
        samples_per_class = 80

        # Class 0: Unmatched (low overlap, low proximity, area mismatch, low text sim)
        c0 = np.column_stack([
            np.random.uniform(0.0, 0.25, samples_per_class),   # IoU
            np.random.uniform(0.0, 0.40, samples_per_class),   # Proximity
            np.random.uniform(0.0, 0.45, samples_per_class),   # Area ratio
            np.random.uniform(0.0, 0.35, samples_per_class),   # Hausdorff sim
            np.random.uniform(0.0, 0.30, samples_per_class),   # Text sim
            np.random.uniform(0.5, 0.95, samples_per_class),   # Reliability A
            np.random.uniform(0.5, 0.95, samples_per_class),   # Reliability B
        ])

        # Class 1: Review / Borderline (partial overlap, area/attribute mismatch)
        n_sub = samples_per_class // 2
        c1_a = np.column_stack([
            np.random.uniform(0.30, 0.70, n_sub),  # IoU
            np.random.uniform(0.45, 0.75, n_sub),  # Proximity
            np.random.uniform(0.50, 0.85, n_sub),  # Area ratio
            np.random.uniform(0.40, 0.75, n_sub),  # Hausdorff sim
            np.random.uniform(0.35, 0.75, n_sub),  # Text sim
            np.random.uniform(0.6, 0.95, n_sub),   # Reliability A
            np.random.uniform(0.6, 0.95, n_sub),   # Reliability B
        ])
        # High spatial overlap but significant area ratio or attribute discrepancy
        c1_b = np.column_stack([
            np.random.uniform(0.70, 1.00, samples_per_class - n_sub),  # IoU
            np.random.uniform(0.70, 1.00, samples_per_class - n_sub),  # Proximity
            np.random.uniform(0.40, 0.65, samples_per_class - n_sub),  # Area ratio
            np.random.uniform(0.70, 1.00, samples_per_class - n_sub),  # Hausdorff sim
            np.random.uniform(0.00, 0.30, samples_per_class - n_sub),  # Text sim
            np.random.uniform(0.6, 0.95, samples_per_class - n_sub),   # Reliability A
            np.random.uniform(0.6, 0.95, samples_per_class - n_sub),   # Reliability B
        ])
        c1 = np.vstack([c1_a, c1_b])

        # Class 2: Matched / High-Confidence (high IoU, close proximity, similar area, high text sim)
        c2 = np.column_stack([
            np.random.uniform(0.75, 1.00, samples_per_class),  # IoU
            np.random.uniform(0.78, 1.00, samples_per_class),  # Proximity
            np.random.uniform(0.80, 1.00, samples_per_class),  # Area ratio
            np.random.uniform(0.75, 1.00, samples_per_class),  # Hausdorff sim
            np.random.uniform(0.65, 1.00, samples_per_class),  # Text sim
            np.random.uniform(0.7, 0.98, samples_per_class),   # Reliability A
            np.random.uniform(0.7, 0.98, samples_per_class),   # Reliability B
        ])

        X = np.vstack([c0, c1, c2])
        y = np.array([0] * samples_per_class + [1] * samples_per_class + [2] * samples_per_class)

        self.model.fit(X, y)
        self._is_trained = True

    def predict(self, feature_vector: list[float] | np.ndarray) -> dict:
        """Run MLP inference on a 7D spatial feature vector.

        Returns:
            dict containing score (0-100), class_label ('matched'|'review'|'unmatched'),
            probabilities per class, and model metadata.
        """
        vec = np.array(feature_vector, dtype=float).reshape(1, -1)
        if vec.shape[1] != 7:
            raise ValueError(f"Expected 7D feature vector, got {vec.shape[1]}D")

        # Bound inputs to [0, 1]
        vec = np.clip(vec, 0.0, 1.0)

        probs = self.model.predict_proba(vec)[0]  # [p_unmatched, p_review, p_matched]
        pred_class = int(np.argmax(probs))

        labels = {0: "unmatched", 1: "review", 2: "matched"}
        class_label = labels.get(pred_class, "unmatched")

        # Softmax probability-based continuous confidence score (0-100)
        # Weight class 2 at 1.0, class 1 at 0.60, class 0 at 0.0
        continuous_score = float(probs[2] * 100.0 + probs[1] * 60.0)
        score = max(0, min(100, int(round(continuous_score))))

        return {
            "score": score,
            "class_label": class_label,
            "probabilities": {
                "unmatched": round(float(probs[0]), 4),
                "review": round(float(probs[1]), 4),
                "matched": round(float(probs[2]), 4),
            },
            "architecture": "Multi-Layer Perceptron (32x16 ReLU)",
        }


# Global singleton instance for quick zero-overhead reuse
_mlp_instance: SpatialMLPModel | None = None


def get_mlp_model() -> SpatialMLPModel:
    global _mlp_instance
    if _mlp_instance is None:
        _mlp_instance = SpatialMLPModel()
    return _mlp_instance
