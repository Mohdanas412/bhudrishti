import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rapidfuzz.fuzz import ratio
from shapely.geometry import shape

from .mlp_model import get_mlp_model
from .normalization import normalize_text, numeric_value

WEIGHTS = {
    "geometry": 0.25,
    "proximity": 0.20,
    "area": 0.15,
    "hausdorff": 0.15,
    "attributes": 0.15,
    "reliability": 0.10,
}
ATTRIBUTE_FIELDS = (
    "ulpin",
    "bhu_aadhar",
    "khasra_no",
    "land_use",
    "name",
    "address",
    "type",
    "category",
    "owner",
)


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
    mlp_class: str = "unmatched"
    mlp_probabilities: Mapping[str, float] = None  # type: ignore


def _geometry(value: Any):
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError("geometry must be a GeoJSON object")
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


def _hausdorff_similarity(first: Any, second: Any) -> float:
    if first is None or second is None:
        return 0.0
    try:
        dist = first.hausdorff_distance(second)
        max_tol = _setting("MATCH_MAX_HAUSDORFF", 0.005)
        return max(0.0, min(1.0, 1.0 - dist / max_tol))
    except Exception:
        return 0.0


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
        sim = ratio(first_value, second_value) / 100
        compared.append(sim)
        if sim >= 0.85:
            matched.append(field)
        else:
            differing.append(field)
    return (sum(compared) / len(compared) if compared else 0.0, tuple(matched), tuple(differing))


def _reliability_single(record: Mapping[str, Any]) -> float:
    source = record.get("source")
    source_reliability = source.get("reliability_score") if isinstance(source, Mapping) else None
    val = numeric_value(record.get("source_reliability", source_reliability))
    if val is not None:
        return max(0.0, min(100.0, val)) / 100.0
    return 0.80


def score_features(first: Mapping[str, Any], second: Mapping[str, Any]) -> ScoreBreakdown:
    if not isinstance(first, Mapping) or not isinstance(second, Mapping):
        raise TypeError("features must be mapping objects")

    first_geometry = _geometry(first.get("geometry"))
    second_geometry = _geometry(second.get("geometry"))
    attributes, matched, differing = _attribute_similarity(first, second)

    rel_a = _reliability_single(first)
    rel_b = _reliability_single(second)

    iou = _geometry_similarity(first_geometry, second_geometry)
    prox = _proximity(first_geometry, second_geometry)
    area_sim = _area_similarity(first, second)
    hausdorff = _hausdorff_similarity(first_geometry, second_geometry)

    # 7-Dimensional Feature Vector for Multi-Layer Perceptron (MLP)
    feature_vector = [iou, prox, area_sim, hausdorff, attributes, rel_a, rel_b]

    # Run GeoAI Multi-Layer Perceptron Inference
    mlp_model = get_mlp_model()
    mlp_res = mlp_model.predict(feature_vector)

    components = {
        "geometry": round(iou, 4),
        "proximity": round(prox, 4),
        "area": round(area_sim, 4),
        "hausdorff": round(hausdorff, 4),
        "attributes": round(attributes, 4),
        "reliability": round((rel_a + rel_b) / 2.0, 4),
        "mlp_confidence": round(mlp_res["score"] / 100.0, 4),
    }

    # Final score blends MLP neural network prediction (60%) with feature weight vector (40%)
    heuristic_score = sum(WEIGHTS[name] * value for name, value in components.items() if name in WEIGHTS) * 100
    blended_score = round(0.60 * mlp_res["score"] + 0.40 * heuristic_score)
    score = max(0, min(100, blended_score))

    # If features have zero spatial overlap and zero attribute match, score is 0
    if iou == 0.0 and prox == 0.0 and area_sim == 0.0 and hausdorff == 0.0 and attributes == 0.0:
        score = 0
        mlp_res["class_label"] = "unmatched"
        mlp_res["probabilities"] = {"unmatched": 1.0, "review": 0.0, "matched": 0.0}

    # ULPIN / Bhu-Aadhar Rule-based Verification
    ulpin_a = str(first.get("ulpin") or first.get("bhu_aadhar") or "").strip().upper()
    ulpin_b = str(second.get("ulpin") or second.get("bhu_aadhar") or "").strip().upper()
    if ulpin_a and ulpin_b and ulpin_a == ulpin_b and len(ulpin_a) >= 11:
        score = max(score, 98)
        mlp_res["class_label"] = "matched"

    # Khasra / Plot Number Rule-based Verification
    khasra_a = normalize_text(first.get("khasra") or first.get("khasra_no") or first.get("plot_no"))
    khasra_b = normalize_text(second.get("khasra") or second.get("khasra_no") or second.get("plot_no"))
    if khasra_a and khasra_b and khasra_a == khasra_b and len(khasra_a) >= 1:
        score = min(100, max(score, 88))
        if score >= 90:
            mlp_res["class_label"] = "matched"
        elif score >= 70:
            mlp_res["class_label"] = "review"

    return ScoreBreakdown(
        score=score,
        components=components,
        matched_attributes=matched,
        differing_attributes=differing,
        mlp_class=mlp_res["class_label"],
        mlp_probabilities=mlp_res["probabilities"],
    )
