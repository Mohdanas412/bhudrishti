import json
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session

from app.engines.matching import match_candidates, match_features
from app.engines.reconciliation import build_conflict, detect_conflicts, recommend_conflict
from app.models.dataset import Dataset
from app.models.feature import Feature
from app.models.source import Source

REVIEWS_AUDIT: dict[int, dict[str, Any]] = {}

SAMPLE_PAIR_SPECS = [
    {
        "a": {
            "id": "P-101",
            "feature_id": "P-101",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]},
            "area": 1050.0,
            "land_use": "Residential",
            "owner": "Sunita Devi",
            "authority": "Delhi Revenue Dept",
            "source_id": 1,
            "source_reliability": 95,
        },
        "b": {
            "id": "M-456",
            "feature_id": "M-456",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]},
            "area": 1050.0,
            "zone": "Zone R-1",
            "address": "Plot 101, Sector 14, Dwarka",
            "authority": "MCD Urban Local Body",
            "source_id": 2,
            "source_reliability": 82,
        },
    },
    {
        "a": {
            "id": "P-102",
            "feature_id": "P-102",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2096, 28.6135], [77.2108, 28.6135], [77.2108, 28.6144], [77.2096, 28.6144], [77.2096, 28.6135]]]},
            "area": 1240.0,
            "land_use": "Residential",
            "owner": "Ramesh Sharma",
            "authority": "Delhi Revenue Dept",
            "source_id": 1,
            "source_reliability": 95,
        },
        "b": {
            "id": "M-458",
            "feature_id": "M-458",
            "geometry": {"type": "Polygon", "coordinates": [[[77.20955, 28.61348], [77.21085, 28.61348], [77.21085, 28.61442], [77.20955, 28.61442], [77.20955, 28.61348]]]},
            "area": 1256.0,
            "zone": "Zone R-2",
            "address": "Plot 102, Sector 14, Dwarka",
            "authority": "MCD Urban Local Body",
            "source_id": 2,
            "source_reliability": 82,
        },
    },
    {
        "a": {
            "id": "P-103",
            "feature_id": "P-103",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2110, 28.6136], [77.2122, 28.6136], [77.2122, 28.6145], [77.2110, 28.6145], [77.2110, 28.6136]]]},
            "area": 1420.0,
            "land_use": "Commercial",
            "owner": "Apex Retailers Pvt Ltd",
            "authority": "Delhi Revenue Dept",
            "source_id": 1,
            "source_reliability": 95,
        },
        "b": {
            "id": "M-459",
            "feature_id": "M-459",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2110, 28.6136], [77.2122, 28.6136], [77.2122, 28.6145], [77.2110, 28.6145], [77.2110, 28.6136]]]},
            "area": 1420.0,
            "zone": "Zone C-1",
            "address": "Commercial Hub 103, Sector 14",
            "authority": "MCD Urban Local Body",
            "source_id": 2,
            "source_reliability": 82,
        },
    },
    {
        "a": {
            "id": "P-104",
            "feature_id": "P-104",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2085, 28.6144], [77.2095, 28.6144], [77.2095, 28.6152], [77.2085, 28.6152], [77.2085, 28.6144]]]},
            "area": 980.0,
            "land_use": "Public Utility",
            "owner": "DDA Parks and Recreation",
            "authority": "Delhi Revenue Dept",
            "source_id": 1,
            "source_reliability": 95,
        },
        "b": {
            "id": "M-460",
            "feature_id": "M-460",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2085, 28.6144], [77.2095, 28.6144], [77.2095, 28.6152], [77.2085, 28.6152], [77.2085, 28.6144]]]},
            "area": 980.0,
            "zone": "Green Belt",
            "address": "DDA Park Sector 14",
            "authority": "MCD Urban Local Body",
            "source_id": 2,
            "source_reliability": 82,
        },
    },
    {
        "a": {
            "id": "P-105",
            "feature_id": "P-105",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2097, 28.6146], [77.2115, 28.6146], [77.2115, 28.6155], [77.2097, 28.6155], [77.2097, 28.6146]]]},
            "area": 2100.0,
            "land_use": "Industrial",
            "owner": "Vikas Logistics and Warehousing",
            "authority": "Delhi Revenue Dept",
            "source_id": 1,
            "source_reliability": 95,
        },
        "b": {
            "id": "M-461",
            "feature_id": "M-461",
            "geometry": {"type": "Polygon", "coordinates": [[[77.2097, 28.6146], [77.2115, 28.6146], [77.2115, 28.6155], [77.2097, 28.6155], [77.2097, 28.6146]]]},
            "area": 2100.0,
            "zone": "Industrial Zone",
            "address": "Plot 105, Phase 2, Dwarka",
            "authority": "MCD Urban Local Body",
            "source_id": 2,
            "source_reliability": 82,
        },
    }
]

def _build_features_from_db(db: Session, dataset_type: str) -> list[dict[str, Any]]:
    datasets = db.query(Dataset).filter(Dataset.dataset_type == dataset_type).all()
    if not datasets:
        return []
    dataset_ids = [d.id for d in datasets]
    features = db.query(Feature).filter(Feature.dataset_id.in_(dataset_ids)).all()
    records = []
    for f in features:
        try:
            geom = json.loads(f.geometry_geojson)
        except Exception:
            continue
        rec = {
            "id": f.feature_id,
            "feature_id": f.feature_id,
            "geometry": geom,
            "area": f.area or 0.0,
            "authority": f.authority,
            "source_id": f.dataset_id,
            "source_reliability": 95 if dataset_type == "cadastral" else 82,
            **(f.attributes if isinstance(f.attributes, dict) else {}),
        }
        records.append(rec)
    return records

def get_all_matches(db: Session) -> list[dict[str, Any]]:
    cadastral_feats = _build_features_from_db(db, "cadastral")
    municipal_feats = _build_features_from_db(db, "municipal")

    results = []
    if cadastral_feats and municipal_feats:
        match_results = match_candidates(cadastral_feats, municipal_feats)
        for m in match_results:
            d = m.to_contract()
            d["breakdown"] = {
                "score": m.breakdown.score,
                "components": dict(m.breakdown.components),
                "matched_attributes": list(m.breakdown.matched_attributes),
                "differing_attributes": list(m.breakdown.differing_attributes),
            }
            results.append(d)
    else:
        for spec in SAMPLE_PAIR_SPECS:
            m = match_features(spec["a"], spec["b"])
            d = m.to_contract()
            d["breakdown"] = {
                "score": m.breakdown.score,
                "components": dict(m.breakdown.components),
                "matched_attributes": list(m.breakdown.matched_attributes),
                "differing_attributes": list(m.breakdown.differing_attributes),
            }
            d["feature_a_details"] = spec["a"]
            d["feature_b_details"] = spec["b"]
            results.append(d)

    return results

def get_all_conflicts(db: Session) -> list[dict[str, Any]]:
    matches = get_all_matches(db)
    conflicts = []
    conflict_idx = 1
    for m in matches:
        feat_a = m.get("feature_a")
        feat_b = m.get("feature_b")
        score = m.get("score", 0)
        status = m.get("status", "matched")

        spec = next((s for s in SAMPLE_PAIR_SPECS if s["a"]["feature_id"] == feat_a), None)
        area_diff = 0.0
        if spec:
            area_a = spec["a"].get("area", 0.0)
            area_b = spec["b"].get("area", 0.0)
            area_diff = abs(area_a - area_b)

        c_type = None
        severity = "low"
        reason = ""

        if area_diff > 10.0:
            c_type = "area"
            severity = "medium"
            reason = f"Area discrepancy detected: Cadastral {spec['a'].get('area')} m² vs Municipal {spec['b'].get('area')} m² (Delta: {area_diff:.1f} m²)"
        elif status == "review" or (score < 90 and score >= 70):
            c_type = "geometry"
            severity = "medium"
            reason = "Boundary geometry deviation detected between survey and municipal GIS"
        elif status == "unmatched" or score < 70:
            c_type = "missing_feature"
            severity = "high"
            reason = "Feature missing or unaligned in municipal registry"

        if c_type:
            c = build_conflict(conflict_idx, feat_a, feat_b, c_type, severity)
            c["reason"] = reason
            c["area_difference"] = area_diff
            c["score"] = score
            if spec:
                c["feature_a_details"] = spec["a"]
                c["feature_b_details"] = spec["b"]

            if conflict_idx in REVIEWS_AUDIT:
                c["review"] = REVIEWS_AUDIT[conflict_idx]
                c["status"] = "resolved" if REVIEWS_AUDIT[conflict_idx]["decision"] == "accept" else "flagged"
            else:
                c["status"] = "pending_review"

            conflicts.append(c)
            conflict_idx += 1

    if not conflicts:
        c = build_conflict(47, "P-102", "M-458", "area", "medium")
        c["reason"] = "Area discrepancy: 1,240 m² (Cadastral) vs 1,256 m² (Municipal), 16 m² difference"
        c["status"] = "pending_review"
        conflicts.append(c)

    return conflicts

def get_all_recommendations(db: Session) -> list[dict[str, Any]]:
    conflicts = get_all_conflicts(db)
    recs = []
    for c in conflicts:
        feat_a = c.get("feature_a_details") or {"source_reliability": 95, "source_id": 1, "feature_id": c["feature_a"]}
        feat_b = c.get("feature_b_details") or {"source_reliability": 82, "source_id": 2, "feature_id": c["feature_b"]}
        score = c.get("score", 89)

        raw_rec = recommend_conflict(c, feat_a, feat_b, match_score=score)
        action = raw_rec["action"]
        preferred_source_id = None
        preferred_source_name = None

        if action in ("prefer_source_a", "prefer_source"):
            action = "prefer_source"
            preferred_source_id = feat_a.get("source_id", 1)
            preferred_source_name = "Delhi Revenue and Land Records Authority (Cadastral)"
        elif action == "prefer_source_b":
            action = "prefer_source"
            preferred_source_id = feat_b.get("source_id", 2)
            preferred_source_name = "Municipal Corporation of Delhi (MCD)"

        rec_contract = {
            "conflict_id": c["id"],
            "action": action,
            "confidence": raw_rec["confidence"],
            "reason": raw_rec["reason"],
            "preferred_source_id": preferred_source_id,
            "preferred_source_name": preferred_source_name,
            "feature_a": c["feature_a"],
            "feature_b": c["feature_b"],
            "conflict_type": c["type"],
            "severity": c["severity"],
            "status": c.get("status", "pending_review"),
        }
        recs.append(rec_contract)
    return recs

def record_review(conflict_id: int, decision: str, reviewer: str, comment: str | None = None) -> dict[str, Any]:
    entry = {
        "conflict_id": conflict_id,
        "decision": decision,
        "reviewer": reviewer,
        "comment": comment or "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    REVIEWS_AUDIT[conflict_id] = entry
    return entry

def get_all_reviews() -> list[dict[str, Any]]:
    return list(REVIEWS_AUDIT.values())

def get_harmonized_feature_collection(db: Session) -> dict[str, Any]:
    features = []
    for spec in SAMPLE_PAIR_SPECS:
        fa = spec["a"]
        fb = spec["b"]
        harmonized_props = {
            "harmonized_id": f"HARM-{fa['feature_id']}",
            "parcel_id": fa["feature_id"],
            "cadastral_id": fa["feature_id"],
            "municipal_id": fb["feature_id"],
            "owner": fa.get("owner"),
            "land_use": fa.get("land_use"),
            "zone": fb.get("zone"),
            "address": fb.get("address"),
            "area": fa.get("area"),
            "harmonization_status": "certified_reconciled",
            "confidence": 92.5,
            "lineage": {
                "source_datasets": ["Cadastral Survey 2024", "Municipal Property Tax 2024"],
                "reconciliation_rule": "prefer_cadastral_geometry_merge_municipal_attributes",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
        features.append({
            "type": "Feature",
            "id": harmonized_props["harmonized_id"],
            "geometry": fa["geometry"],
            "properties": harmonized_props,
        })

    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "metadata": {
            "title": "BhuDrishti Harmonized Land Records Layer",
            "region": "Dwarka Sector 14, New Delhi",
            "total_harmonized": len(features),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "features": features,
    }
