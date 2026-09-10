import pytest
from app.engines.matching import classify_score, match_candidates, match_features

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
}


def feature(feature_id="P102", **overrides):
    value = {
        "feature_id": feature_id,
        "geometry": SQUARE,
        "area": 100,
        "land_use": "Residential",
        "source_reliability": 90,
    }
    value.update(overrides)
    return value


def test_exact_match_is_high_confidence():
    result = match_features(feature(), feature("M458"))
    assert result.status == "matched"
    assert result.score >= 95
    assert result.feature_a == "P102"
    assert result.feature_b == "M458"


def test_partial_match_is_review():
    result = match_features(feature(), feature("M458", land_use="Industrial", area=50))
    assert 70 <= result.score < 90
    assert result.status == "review"
    assert "land_use" in result.breakdown.differing_attributes


def test_different_records_are_unmatched():
    result = match_features(
        feature(),
        feature("M458", geometry={"type": "Point", "coordinates": [10, 10]}, area=1, land_use="Industrial"),
    )
    assert result.status == "unmatched"


def test_missing_optional_fields_are_safe():
    result = match_features({"id": "P102"}, {"id": "M458"})
    assert result.score == 0
    assert result.status == "unmatched"


def test_threshold_boundaries(monkeypatch):
    monkeypatch.setenv("MATCH_HIGH_CONFIDENCE", "90")
    monkeypatch.setenv("MATCH_REVIEW_THRESHOLD", "70")
    assert classify_score(90) == "matched"
    assert classify_score(89) == "review"
    assert classify_score(70) == "review"
    assert classify_score(69) == "unmatched"


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError, match="valid GeoJSON"):
        match_features(feature(), feature("M458", geometry={"bad": True}))


def test_candidates_are_sorted_deterministically():
    first = match_candidates([feature("P2"), feature("P1")], [feature("M2"), feature("M1")])
    second = match_candidates([feature("P2"), feature("P1")], [feature("M2"), feature("M1")])
    assert [item.to_contract() for item in first] == [item.to_contract() for item in second]


def test_invalid_thresholds_are_rejected(monkeypatch):
    monkeypatch.setenv("MATCH_HIGH_CONFIDENCE", "60")
    monkeypatch.setenv("MATCH_REVIEW_THRESHOLD", "70")
    with pytest.raises(ValueError, match="thresholds"):
        classify_score(70)