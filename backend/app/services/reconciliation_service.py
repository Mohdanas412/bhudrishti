import json
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any

from sqlalchemy.orm import Session

from app.engines.matching import match_candidates, match_features
from app.engines.reconciliation import build_conflict, recommend_conflict
from app.models.dataset import Dataset
from app.models.feature import Feature
from app.models.source import Source

REVIEWS_AUDIT: dict[int, dict[str, Any]] = {}

# Cap the matches surfaced to the UI. The N^2 candidate generation can emit
# thousands of pairs (e.g. two 1,181-feature building surveys -> ~1.4M), which
# freezes the API and swamps the map/table. Keep the result set small and let
# the frontend zoom into specific features on demand.
MAX_MATCHES = 100

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

def _build_features_from_db(
    db: Session, dataset_type: str, per_dataset_limit: int = 40
) -> list[dict[str, Any]]:
    datasets = db.query(Dataset).filter(Dataset.dataset_type == dataset_type).all()
    if not datasets:
        return []
    dataset_ids = [d.id for d in datasets]
    # Cap PER DATASET (source) so a huge first source doesn't consume the whole
    # budget before later sources — which need to cross-match against each other
    # (e.g. the two independent Bengaluru building surveys) — get a fair share.
    # A single type-wide .limit() truncates to the first source and silently drops
    # the duplicate partner, making building-building matching meaningless.
    features = []
    for did in dataset_ids:
        features.extend(
            db.query(Feature)
            .filter(Feature.dataset_id == did)
            .limit(per_dataset_limit)
            .all()
        )
    from shapely.geometry import shape

    # Defensive: drop duplicate rows (same dataset + feature_id) that can be
    # left behind by non-idempotent ingestion runs.
    seen: set[tuple[int, str]] = set()
    records = []
    for f in features:
        key = (f.dataset_id, f.feature_id)
        if key in seen:
            continue
        seen.add(key)
        try:
            geom = json.loads(f.geometry_geojson)
            if not shape(geom).is_valid:
                continue
        except (ValueError, TypeError):
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

def _attach_match_details(db: Session, matches: list[dict[str, Any]]) -> None:
    """Attach feature_a_details/feature_b_details (incl. parsed geometry) to real matches.

    The frontend map renders polygons from match.feature_a_details.geometry and
    match.feature_b_details.geometry; the raw MatchResult contract only carries
    feature_a/feature_b/score/status, so we look up the source Feature rows (batch)
    and attach their geometry + attributes here.
    """
    ids = set()
    for m in matches:
        ids.add(m["feature_a"])
        ids.add(m["feature_b"])
    if not ids:
        return
    rows = db.query(Feature).filter(Feature.feature_id.in_(ids)).all()
    details: dict[str, dict[str, Any]] = {}
    for r in rows:
        det: dict[str, Any] = {
            "feature_id": r.feature_id,
            "area": r.area,
            "authority": r.authority,
            "source_id": r.dataset_id,
            **(r.attributes if isinstance(r.attributes, dict) else {}),
        }
        try:
            det["geometry"] = json.loads(r.geometry_geojson)
        except (JSONDecodeError, TypeError):
            det["geometry"] = None
        details[r.feature_id] = det
    for m in matches:
        m["feature_a_details"] = details.get(m["feature_a"])
        m["feature_b_details"] = details.get(m["feature_b"])

def get_all_matches(db: Session) -> list[dict[str, Any]]:
    cadastral_feats = _build_features_from_db(db, "cadastral")
    municipal_feats = _build_features_from_db(db, "municipal")
    building_feats = _build_features_from_db(db, "building")

    cadastral_results = []
    building_results = []
    results = []

    def add_match(m, target_list) -> None:
        d = m.to_contract()
        d["breakdown"] = {
            "score": m.breakdown.score,
            "components": dict(m.breakdown.components),
            "matched_attributes": list(m.breakdown.matched_attributes),
            "differing_attributes": list(m.breakdown.differing_attributes),
        }
        target_list.append(d)

    # 1. Matching Cadastral <-> Municipal (current logic)
    if cadastral_feats and municipal_feats:
        match_results = match_candidates(cadastral_feats, municipal_feats)
        for m in match_results:
            add_match(m, cadastral_results)

    # 2. Matching Building <-> Building (independent sources of same type)
    if building_feats:
        # Partition by source_id so we don't try to match features from the same source iteration
        by_source = {}
        for f in building_feats:
            sid = f["source_id"]
            if sid not in by_source:
                by_source[sid] = []
            by_source[sid].append(f)

        sources = list(by_source.values())
        if len(sources) >= 2:
            # Sort sources by size descending to get the real Bengaluru ones (1000+ feats)
            sources.sort(key=len, reverse=True)
            # Match the two largest building sources against each other
            match_results = match_candidates(sources[0], sources[1])
            for m in match_results:
                add_match(m, building_results)

    # 3. Form a blended 50/50 queue (Rural vs Urban)
    cadastral_results.sort(key=lambda x: x["score"], reverse=True)
    building_results.sort(key=lambda x: x["score"], reverse=True)

    results = cadastral_results[:50] + building_results[:50]
    # Optionally sort the combined list so highest confidence is at top across both
    results.sort(key=lambda x: x["score"], reverse=True)

    # Attach real geometry/details so the map can render the polygons
    if results:
        _attach_match_details(db, results)
        return results

    # Fallback only if NO matches found across any real layers
    for spec in SAMPLE_PAIR_SPECS:
        m = match_features(spec["a"], spec["b"])
        add_match(m)
        d = results[-1]
        d["feature_a_details"] = spec["a"]
        d["feature_b_details"] = spec["b"]

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

        # 1. Fetch real details from features table or fallback to spec
        f_a_row = db.query(Feature).filter(Feature.feature_id == feat_a).first()
        f_b_row = db.query(Feature).filter(Feature.feature_id == feat_b).first()

        spec = next((s for s in SAMPLE_PAIR_SPECS if s["a"]["feature_id"] == feat_a), None)

        area_a = 0.0
        area_b = 0.0
        if f_a_row and f_b_row:
            area_a = f_a_row.area or 0.0
            area_b = f_b_row.area or 0.0
        elif spec:
            area_a = spec["a"].get("area", 0.0)
            area_b = spec["b"].get("area", 0.0)

        area_diff = abs(area_a - area_b)

        c_type = None
        severity = "low"
        reason = ""

        if area_diff > 10.0:
            c_type = "area"
            severity = "medium"
            reason = f"Area discrepancy detected: {area_a:.1f} m² vs {area_b:.1f} m² (Delta: {area_diff:.1f} m²)"
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
            if f_a_row and f_b_row:
                c["feature_a_details"] = {
                    "feature_id": f_a_row.feature_id,
                    "area": f_a_row.area,
                    "source_id": f_a_row.dataset_id,
                    **(f_a_row.attributes if isinstance(f_a_row.attributes, dict) else {})
                }
                c["feature_b_details"] = {
                    "feature_id": f_b_row.feature_id,
                    "area": f_b_row.area,
                    "source_id": f_b_row.dataset_id,
                    **(f_b_row.attributes if isinstance(f_b_row.attributes, dict) else {})
                }
            elif spec:
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
            # Fetch real source name if we have a dataset_id -> source_id
            ds = db.query(Dataset).filter(Dataset.id == preferred_source_id).first()
            if ds and ds.source_id:
                src = db.query(Source).filter(Source.id == ds.source_id).first()
                preferred_source_name = src.name if src else None
            if not preferred_source_name:
                preferred_source_name = "Primary Source"
        elif action == "prefer_source_b":
            action = "prefer_source"
            preferred_source_id = feat_b.get("source_id", 2)
            ds = db.query(Dataset).filter(Dataset.id == preferred_source_id).first()
            if ds and ds.source_id:
                src = db.query(Source).filter(Source.id == ds.source_id).first()
                preferred_source_name = src.name if src else None
            if not preferred_source_name:
                preferred_source_name = "Secondary Source"

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
    # Use real matches / conflicts to build harmonized layer
    matches = get_all_matches(db)

    features = []

    # If no DB matches, fallback to sample specs for the mock UI
    if not matches:
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
    else:
        # Build from real DB matches (high-confidence or resolved ones)
        # We assume for validation that anything score >= 70 is harmonized trivially
        # by taking the geometry of feature_a.
        for m in matches:
            if m.get("score", 0) >= 70:
                fa_id = m.get("feature_a")
                db_feat = db.query(Feature).filter(Feature.feature_id == fa_id).first()
                if not db_feat or not db_feat.geometry_geojson:
                    continue
                try:
                    geom = json.loads(db_feat.geometry_geojson)
                except (JSONDecodeError, TypeError):
                    continue

                harmonized_props = {
                    "harmonized_id": f"HARM-{fa_id}",
                    "source_feature_a": fa_id,
                    "source_feature_b": m.get("feature_b"),
                    "harmonization_status": "certified_reconciled",
                    "confidence": m.get("score"),
                    "area": db_feat.area,
                    **(db_feat.attributes if isinstance(db_feat.attributes, dict) else {})
                }

                features.append({
                    "type": "Feature",
                    "id": harmonized_props["harmonized_id"],
                    "geometry": geom,
                    "properties": harmonized_props,
                })

    # For now, generic region title since it's dynamic
    is_real = len(matches) > 0
    region = "Bengaluru Validation Region" if is_real else "Dwarka Sector 14, New Delhi"

    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "metadata": {
            "title": "BhuDrishti Harmonized Land Records Layer",
            "region": region,
            "total_harmonized": len(features),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "features": features,
    }
