import os
from dataclasses import dataclass
from typing import Any, Mapping

from rapidfuzz.fuzz import ratio
from shapely.geometry import shape

from .normalization import normalize_text, numeric_value

WEIGHTS = {
    "geometry": 0.30,
    "proximity": 0.25,
    "area": 0.20,
    "attributes": 0.15,
    "reliability": 0.10,
}
ATTRIBUTE_FIELDS = ("land_use", "name", "address", "type", "category")


def _setting(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class ScoreBreakdown:
    score: int
    components: Mapping[str, float]
    matched_attributes: tuple[str, ...]
    differing_attributes: tuple[str, ...]


def _geometry(value: Any):
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("geometry must be a GeoJSON object")
    try:
        geometry = shape(value)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("geometry is not valid GeoJSON") from exc
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("geometry must be non-empty and valid")
    return geometry


def _geometry_similarity(first: Any, second: Any) -> float:
    if first is None or second is None:
        return 0.0
    union = first.union(second).area
    if union == 0:
        return 1.0 if first.equals(second) else 0.0
    return max(0.0, min(1.0, first.intersection(second).area / union))


def _proximity(first: Any, second: Any) -> float:
    if first is None or second is None:
        return 0.0
    distance = first.centroid.distance(second.centroid)
    maximum = max(_setting("MATCH_MAX_DISTANCE", 0.01), 1e-12)
    return max(0.0, min(1.0, 1.0 - distance / maximum))


def _area_similarity(first: Mapping[str, Any], second: Mapping[str, Any]) -> float:
    first_area = numeric_value(first.get("area"))
    second_area = numeric_value(second.get("area"))
    if first_area is None or second_area is None or first_area < 0 or second_area < 0:
        return 0.0
    if first_area == second_area:
        return 1.0
    maximum = max(first_area, second_area)
    return max(0.0, min(1.0, min(first_area, second_area) / maximum))


def _attribute_similarity(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> tuple[float, tuple[str, ...], tuple[str, ...]]:
    compared = []
    matched = []
    differing = []
    for field in ATTRIBUTE_FIELDS:
        first_value = normalize_text(first.get(field))
        second_value = normalize_text(second.get(field))
        if not first_value or not second_value:
            continue
        compared.append(ratio(first_value, second_value) / 100)
        if first_value == second_value:
            matched.append(field)
        else:
            differing.append(field)
    return (sum(compared) / len(compared) if compared else 0.0, tuple(matched), tuple(differing))


def _reliability(first: Mapping[str, Any], second: Mapping[str, Any]) -> float:
    values = []
    for record in (first, second):
        source = record.get("source")
        source_reliability = source.get("reliability_score") if isinstance(source, Mapping) else None
        value = numeric_value(record.get("source_reliability", source_reliability))
        if value is not None:
            values.append(max(0.0, min(100.0, value)) / 100)
    return sum(values) / len(values) if values else 0.0


def score_features(first: Mapping[str, Any], second: Mapping[str, Any]) -> ScoreBreakdown:
    if not isinstance(first, Mapping) or not isinstance(second, Mapping):
        raise ValueError("features must be mapping objects")
    first_geometry = _geometry(first.get("geometry"))
    second_geometry = _geometry(second.get("geometry"))
    attributes, matched, differing = _attribute_similarity(first, second)
    components = {
        "geometry": _geometry_similarity(first_geometry, second_geometry),
        "proximity": _proximity(first_geometry, second_geometry),
        "area": _area_similarity(first, second),
        "attributes": attributes,
        "reliability": _reliability(first, second),
    }
    score = round(sum(WEIGHTS[name] * value for name, value in components.items()) * 100)
    return ScoreBreakdown(max(0, min(100, score)), components, matched, differing)