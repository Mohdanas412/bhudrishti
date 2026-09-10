from app.engines.matching import match_features
from app.engines.matching.mlp_model import SpatialMLPModel, get_mlp_model
from app.engines.matching.scoring import score_features


def test_mlp_model_initialization_and_prediction():
    model = get_mlp_model()
    assert isinstance(model, SpatialMLPModel)
    assert model._is_trained is True

    # Test high-confidence feature vector [IoU, prox, area, hausdorff, text, rel_a, rel_b]
    high_conf_vec = [0.95, 0.98, 0.99, 0.92, 0.90, 0.95, 0.95]
    res = model.predict(high_conf_vec)

    assert "score" in res
    assert 0 <= res["score"] <= 100
    assert res["class_label"] in ("matched", "review", "unmatched")
    assert "probabilities" in res
    assert res["architecture"] == "Multi-Layer Perceptron (32x16 ReLU)"


def test_mlp_model_unmatched_prediction():
    model = get_mlp_model()
    low_conf_vec = [0.05, 0.10, 0.15, 0.05, 0.10, 0.80, 0.80]
    res = model.predict(low_conf_vec)

    assert res["score"] < 60
    assert res["class_label"] == "unmatched"


def test_score_features_with_mlp():
    feat_a = {
        "id": "P-101",
        "feature_id": "P-101",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.2085, 28.6135],
                    [77.2095, 28.6135],
                    [77.2095, 28.6142],
                    [77.2085, 28.6142],
                    [77.2085, 28.6135],
                ]
            ],
        },
        "area": 1050.0,
        "land_use": "Residential",
        "owner": "Sunita Devi",
    }
    feat_b = {
        "id": "M-456",
        "feature_id": "M-456",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.2085, 28.6135],
                    [77.2095, 28.6135],
                    [77.2095, 28.6142],
                    [77.2085, 28.6142],
                    [77.2085, 28.6135],
                ]
            ],
        },
        "area": 1050.0,
        "land_use": "Residential",
        "address": "Plot 101, Sector 14",
    }

    breakdown = score_features(feat_a, feat_b)
    assert 0 <= breakdown.score <= 100
    assert "mlp_confidence" in breakdown.components
    assert breakdown.mlp_class in ("matched", "review", "unmatched")
    assert breakdown.mlp_probabilities is not None


def test_match_features_integration():
    feat_a = {
        "feature_id": "P-101",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.2085, 28.6135],
                    [77.2095, 28.6135],
                    [77.2095, 28.6142],
                    [77.2085, 28.6142],
                    [77.2085, 28.6135],
                ]
            ],
        },
        "area": 1050.0,
    }
    feat_b = {
        "feature_id": "M-456",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [77.2085, 28.6135],
                    [77.2095, 28.6135],
                    [77.2095, 28.6142],
                    [77.2085, 28.6142],
                    [77.2085, 28.6135],
                ]
            ],
        },
        "area": 1050.0,
    }

    res = match_features(feat_a, feat_b)
    assert res.feature_a == "P-101"
    assert res.feature_b == "M-456"
    assert res.status in ("matched", "review", "unmatched")
    assert 0 <= res.score <= 100
