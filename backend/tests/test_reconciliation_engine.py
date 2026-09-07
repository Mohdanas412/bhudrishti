from app.engines.matching import match_features
from app.engines.reconciliation import (
    build_conflict,
    detect_conflicts,
    recommend_conflict,
)


def test_review_and_unmatched_matches_create_contract_conflicts():
    matches = [
        match_features({"id": "P1"}, {"id": "M1"}),
        match_features(
            {"id": "P2", "geometry": {"type": "Point", "coordinates": [0, 0]}, "area": 70, "land_use": "Residential", "source_reliability": 90},
            {"id": "M2", "geometry": {"type": "Point", "coordinates": [0, 0]}, "area": 50, "land_use": "Commercial", "source_reliability": 90},
        ),
    ]
    conflicts = detect_conflicts(matches)
    assert conflicts[0]["type"] == "missing_feature"
    assert conflicts[1]["type"] == "attribute"
    assert set(conflicts[0]) == {"id", "type", "severity", "feature_a", "feature_b"}


def test_reliability_selects_preferred_source():
    conflict = build_conflict(47, "P102", "M458", "geometry", "medium")
    recommendation = recommend_conflict(
        conflict,
        {"source_reliability": 95},
        {"source_reliability": 80},
        match_score=89,
    )
    assert recommendation == {
        "conflict_id": 47,
        "action": "prefer_source_a",
        "confidence": 89,
        "reason": "Source A has the higher reliability score",
    }


def test_supported_special_conflicts_have_deterministic_actions():
    duplicate = build_conflict(1, "P1", "M1", "duplicate", "high")
    temporal = build_conflict(2, "P2", "M2", "temporal", "low")
    assert recommend_conflict(duplicate)["action"] == "manual_review_required"
    assert recommend_conflict(temporal)["action"] == "flag_real_world_change"


def test_equal_attribute_sources_are_merged():
    conflict = build_conflict(3, "P3", "M3", "attribute", "medium")
    assert recommend_conflict(conflict)["action"] == "merge_attributes"