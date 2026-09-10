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
    import numpy as np
    from shapely.geometry import box, shape
    from shapely.strtree import STRtree

    list_b = list(features_b)
    if not list_b:
        return []

    # Build spatial index over features_b bounding boxes for O(N log M) candidate pruning
    valid_geoms_b = []
    valid_features_b = []
    geom_to_idx = {}

    for f in list_b:
        g = f.get("geometry")
        if g:
            try:
                sg = shape(g)
                if sg.is_valid and not sg.is_empty:
                    geom_to_idx[id(sg)] = len(valid_geoms_b)
                    valid_geoms_b.append(sg)
                    valid_features_b.append(f)
                    continue
            except Exception:
                pass

    tree = STRtree(valid_geoms_b) if valid_geoms_b else None

    results = []
    for first in features_a:
        g_a = first.get("geometry")
        matched_candidates = []
        if tree and g_a:
            try:
                sg_a = shape(g_a)
                # Query tree for nearby/overlapping candidate bounding boxes (~20m tolerance)
                minx, miny, maxx, maxy = sg_a.bounds
                query_geom = box(minx - 0.0002, miny - 0.0002, maxx + 0.0002, maxy + 0.0002)
                candidates = tree.query(query_geom)
                for cg in candidates:
                    if isinstance(cg, (int, np.integer)):
                        # Modern Shapely 2.0 returns numpy integer array of indices
                        matched_candidates.append(valid_features_b[int(cg)])
                    else:
                        # Legacy Shapely returns geometry objects
                        idx = geom_to_idx.get(id(cg))
                        if idx is not None:
                            matched_candidates.append(valid_features_b[idx])
            except Exception:
                matched_candidates = list_b[:5]
        else:
            matched_candidates = list_b[:5]

        # If spatial tree found no candidates, fallback to checking top candidates to allow attribute matching
        if not matched_candidates:
            matched_candidates = list_b[:5]

        # Deduplicate candidates while preserving order and limit to top 10 candidates per feature
        seen_ids = set()
        deduped_candidates = []
        for cand in matched_candidates:
            cid = id(cand)
            if cid not in seen_ids:
                seen_ids.add(cid)
                deduped_candidates.append(cand)
                if len(deduped_candidates) >= 10:
                    break

        for second in deduped_candidates:
            res = match_features(first, second)
            results.append(res)

    return sorted(results, key=lambda result: (-result.score, result.feature_a, result.feature_b))


def auto_match_candidates(
    matches: Iterable[MatchResult], threshold: int | None = None
) -> dict[str, list[MatchResult]]:
    """Partition matches into auto-approved, review queue, and unmatched based on threshold."""
    high = threshold if threshold is not None else _threshold("MATCH_HIGH_CONFIDENCE", 90)
    review = _threshold("MATCH_REVIEW_THRESHOLD", 70)

    approved = []
    for_review = []
    unmatched = []

    for m in matches:
        if m.score >= high:
            approved.append(m)
        elif m.score >= review:
            for_review.append(m)
        else:
            unmatched.append(m)

    return {
        "auto_approved": approved,
        "review_queue": for_review,
        "unmatched": unmatched,
        "threshold_used": high,
    }