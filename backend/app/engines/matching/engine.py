import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .scoring import ScoreBreakdown, score_features


def _threshold(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class MatchResult:
    feature_a: str
    feature_b: str
    score: int
    status: str
    breakdown: ScoreBreakdown

    def to_contract(self) -> dict[str, Any]:
        return {
            "feature_a": self.feature_a,
            "feature_b": self.feature_b,
            "score": self.score,
            "status": self.status,
        }


def _feature_id(feature: Mapping[str, Any]) -> str:
    for name in ("feature_id", "id", "source_feature_id"):
        value = feature.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    raise ValueError("feature requires feature_id, id, or source_feature_id")


def classify_score(score: int) -> str:
    high = _threshold("MATCH_HIGH_CONFIDENCE", 90)
    review = _threshold("MATCH_REVIEW_THRESHOLD", 70)
    if not 0 <= review <= high <= 100:
        raise ValueError("matching thresholds must satisfy 0 <= review <= high <= 100")
    if score >= high:
        return "matched"
    if score >= review:
        return "review"
    return "unmatched"


def match_features(first: Mapping[str, Any], second: Mapping[str, Any]) -> MatchResult:
    first_id = _feature_id(first)
    second_id = _feature_id(second)
    breakdown = score_features(first, second)
    return MatchResult(first_id, second_id, breakdown.score, classify_score(breakdown.score), breakdown)


def match_candidates(
    features_a: Iterable[Mapping[str, Any]], features_b: Iterable[Mapping[str, Any]]
) -> list[MatchResult]:
    results = [match_features(first, second) for first in features_a for second in features_b]
    return sorted(results, key=lambda result: (-result.score, result.feature_a, result.feature_b))