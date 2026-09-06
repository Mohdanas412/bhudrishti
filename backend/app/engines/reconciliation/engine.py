from collections.abc import Iterable, Mapping
from typing import Any

from app.engines.matching.engine import MatchResult
from app.engines.matching.normalization import numeric_value

CONFLICT_TYPES = {"geometry", "area", "attribute", "missing_feature", "duplicate", "temporal"}
SEVERITIES = {"informational", "low", "medium", "high"}
ACTION_BY_TYPE = {
    "duplicate": "manual_review_required",
    "temporal": "flag_real_world_change",
}


def _required_text(record: Mapping[str, Any], name: str) -> str:
    value = record.get(name)
    if value is None or not str(value).strip():
        raise ValueError(f"conflict requires {name}")
    return str(value).strip()


def build_conflict(
    conflict_id: int,
    feature_a: str,
    feature_b: str,
    conflict_type: str,
    severity: str,
) -> dict[str, Any]:
    if conflict_type not in CONFLICT_TYPES:
        raise ValueError(f"unsupported conflict type: {conflict_type}")
    if severity not in SEVERITIES:
        raise ValueError(f"unsupported severity: {severity}")
    if conflict_id < 0:
        raise ValueError("conflict_id must be non-negative")
    return {
        "id": conflict_id,
        "type": conflict_type,
        "severity": severity,
        "feature_a": feature_a,
        "feature_b": feature_b,
    }


def detect_conflicts(matches: Iterable[MatchResult | Mapping[str, Any]]) -> list[dict[str, Any]]:
    conflicts = []
    for conflict_id, match in enumerate(matches, start=1):
        status = match.status if isinstance(match, MatchResult) else _required_text(match, "status")
        if status == "matched":
            continue
        feature_a = match.feature_a if isinstance(match, MatchResult) else _required_text(match, "feature_a")
        feature_b = match.feature_b if isinstance(match, MatchResult) else _required_text(match, "feature_b")
        conflict_type = "missing_feature" if status == "unmatched" else "attribute"
        severity = "high" if status == "unmatched" else "medium"
        conflicts.append(build_conflict(conflict_id, feature_a, feature_b, conflict_type, severity))
    return conflicts


def _source_reliability(feature: Mapping[str, Any] | None) -> float | None:
    if feature is None:
        return None
    source = feature.get("source")
    source_value = source.get("reliability_score") if isinstance(source, Mapping) else None
    value = numeric_value(feature.get("source_reliability", source_value))
    return None if value is None else max(0.0, min(100.0, value))


def _confidence(conflict: Mapping[str, Any], match_score: int | None) -> int:
    if match_score is not None:
        return max(0, min(100, int(match_score)))
    return {"informational": 60, "low": 70, "medium": 80, "high": 90}[conflict["severity"]]


def recommend_conflict(
    conflict: Mapping[str, Any],
    feature_a: Mapping[str, Any] | None = None,
    feature_b: Mapping[str, Any] | None = None,
    match_score: int | None = None,
) -> dict[str, Any]:
    conflict_id = conflict.get("id")
    if not isinstance(conflict_id, int) or conflict_id < 0:
        raise ValueError("conflict id must be a non-negative integer")
    conflict_type = _required_text(conflict, "type")
    severity = _required_text(conflict, "severity")
    if conflict_type not in CONFLICT_TYPES or severity not in SEVERITIES:
        raise ValueError("conflict contains an unsupported type or severity")

    action = ACTION_BY_TYPE.get(conflict_type)
    reason = "Conflict type requires explicit review"
    first_reliability = _source_reliability(feature_a)
    second_reliability = _source_reliability(feature_b)
    if action is None and first_reliability is not None and second_reliability is not None:
        if first_reliability > second_reliability:
            action = "prefer_source_a"
            reason = "Source A has the higher reliability score"
        elif second_reliability > first_reliability:
            action = "prefer_source_b"
            reason = "Source B has the higher reliability score"
    if action is None:
        if conflict_type in {"attribute", "area"}:
            action = "merge_attributes"
            reason = "Both sources are available and the conflict is attribute-level"
        elif conflict_type == "missing_feature" and feature_a is not None and feature_b is None:
            action = "prefer_source_a"
            reason = "The feature is present only in source A"
        else:
            action = "manual_review_required"

    return {
        "conflict_id": conflict_id,
        "action": action,
        "confidence": _confidence(conflict, match_score),
        "reason": reason,
    }