"""
GIS Topology Correction & Vertex Snapping Engine — Geo-Engine.

Provides:
  1. Multi-layer & Intra-layer Vertex Snapping:
     Snaps polygon/multipolygon vertices to reference layers or neighbouring
     polygons within a distance tolerance using Shapely.
  2. Overlap Resolution:
     Detects micro-overlaps (slivers / mutual boundary incursions) and cleanly
     resolves them via boundary clipping / difference subtraction.
  3. Gap / Sliver Removal:
     Detects micro-gaps / sliver vacant strips between adjacent parcels and
     merges or closes them.
  4. Topology Health Report:
     Produces comprehensive diagnostics detailing before/after health metrics:
     - gaps_detected / gaps_fixed
     - overlaps_detected / overlaps_merged
     - vertices_snapped
     - sliver_polygons_removed
     - health_score (0-100 index)
     - detailed fix audit ledger

Storage-agnostic: operates strictly on GeoDataFrames & Shapely geometries.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, mapping
from shapely.ops import snap, unary_union
from shapely.validation import make_valid


@dataclass
class TopologyMetricSummary:
    """Summary counts and metrics before and after topology correction."""

    total_features: int = 0
    valid_features: int = 0
    invalid_features: int = 0
    overlaps_detected: int = 0
    overlaps_resolved: int = 0
    gaps_detected: int = 0
    gaps_resolved: int = 0
    vertices_snapped: int = 0
    slivers_cleaned: int = 0
    total_overlap_area_sqm: float = 0.0
    total_gap_area_sqm: float = 0.0
    initial_health_score: float = 100.0
    final_health_score: float = 100.0


@dataclass
class TopologyFixEvent:
    """Detailed record of an individual geometric topology fix applied."""

    fix_type: str  # 'snap', 'overlap_merge', 'gap_fill', 'make_valid', 'sliver_clean'
    feature_index: int | None
    feature_id: str | None
    description: str
    delta_area_sqm: float = 0.0
    vertices_affected: int = 0


@dataclass
class TopologyHealthReport:
    """Complete diagnostic and audit report for topology operations."""

    status: str  # 'clean', 'corrected', 'issues_remaining'
    summary: TopologyMetricSummary = field(default_factory=TopologyMetricSummary)
    fixes: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    snap_tolerance: float = 0.00005
    area_tolerance_sqm: float = 5.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": asdict(self.summary),
            "fixes": self.fixes,
            "issues": self.issues,
            "snap_tolerance": self.snap_tolerance,
            "area_tolerance_sqm": self.area_tolerance_sqm,
        }


def _approx_sqm_to_deg(area_sqm: float, lat_deg: float = 28.6) -> float:
    """Approximate conversion from square meters to square degrees at given latitude."""
    # 1 deg lat ~ 111,000m; 1 deg lon ~ 111,000m * cos(lat)
    lat_m = 111000.0
    lon_m = 111000.0 * math.cos(math.radians(lat_deg))
    return area_sqm / (lat_m * lon_m)


def _approx_deg_to_sqm(area_deg: float, lat_deg: float = 28.6) -> float:
    """Approximate conversion from square degrees to square meters at given latitude."""
    lat_m = 111000.0
    lon_m = 111000.0 * math.cos(math.radians(lat_deg))
    return area_deg * (lat_m * lon_m)


def _count_vertices(geom: Any) -> int:
    """Count total coordinates/vertices in geometry."""
    if geom is None or geom.is_empty:
        return 0
    if geom.geom_type == "Polygon":
        count = len(geom.exterior.coords)
        for interior in geom.interiors:
            count += len(interior.coords)
        return count
    elif geom.geom_type == "MultiPolygon":
        return sum(_count_vertices(p) for p in geom.geoms)
    elif geom.geom_type in ("LineString", "LinearRing"):
        return len(geom.coords)
    elif geom.geom_type == "MultiLineString":
        return sum(len(ls.coords) for ls in geom.geoms)
    elif geom.geom_type == "Point":
        return 1
    elif geom.geom_type == "MultiPoint":
        return len(geom.geoms)
    elif geom.geom_type == "GeometryCollection":
        return sum(_count_vertices(g) for g in geom.geoms)
    return 0


def snap_geometry_to_reference(
    target_geom: Any,
    reference_geom: Any,
    tolerance: float = 0.00005,
) -> tuple[Any, int]:
    """Snap vertices of target_geom to reference_geom within tolerance.

    Returns:
        (snapped_geom, num_snapped_vertices)
    """
    if target_geom is None or target_geom.is_empty:
        return target_geom, 0
    if reference_geom is None or reference_geom.is_empty:
        return target_geom, 0

    try:
        snapped = snap(target_geom, reference_geom, tolerance)
        if not snapped.is_valid:
            snapped = make_valid(snapped)

        # Count if coordinates shifted
        v_before = _count_vertices(target_geom)
        v_after = _count_vertices(snapped)
        vertices_changed = abs(v_after - v_before)
        if vertices_changed == 0 and not target_geom.equals_exact(snapped, 1e-12):
            vertices_changed = 1

        return snapped, vertices_changed
    except Exception:
        return target_geom, 0


def snap_layers(
    target_gdf: gpd.GeoDataFrame,
    reference_gdf: gpd.GeoDataFrame | None = None,
    tolerance: float = 0.00005,
) -> tuple[gpd.GeoDataFrame, list[TopologyFixEvent]]:
    """Snap target GeoDataFrame geometries to a reference GeoDataFrame or to itself.

    If reference_gdf is provided: Multi-layer snapping (target snaps to reference).
    If reference_gdf is None: Intra-layer snapping (each polygon snaps to neighbors).
    """
    if target_gdf.empty:
        return target_gdf.copy(), []

    result_gdf = target_gdf.copy()
    fixes: list[TopologyFixEvent] = []

    if reference_gdf is not None and not reference_gdf.empty:
        # Multi-layer snap
        # Union reference geoms or build spatial index for fast snapping
        ref_union = unary_union([g for g in reference_gdf.geometry if g is not None and not g.is_empty])

        for idx, row in result_gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue

            snapped_geom, v_count = snap_geometry_to_reference(geom, ref_union, tolerance=tolerance)
            if not geom.equals_exact(snapped_geom, 1e-12):
                result_gdf.at[idx, "geometry"] = snapped_geom
                feat_id = row.get("feature_id", str(idx))
                delta_area = abs(snapped_geom.area - geom.area)
                delta_sqm = _approx_deg_to_sqm(delta_area)
                fixes.append(
                    TopologyFixEvent(
                        fix_type="snap",
                        feature_index=int(idx) if isinstance(idx, (int, np.integer)) else None,
                        feature_id=str(feat_id),
                        description=f"Snapped vertices to reference layer (tolerance={tolerance:.6f})",
                        delta_area_sqm=round(delta_sqm, 4),
                        vertices_affected=max(1, v_count),
                    )
                )
    else:
        # Intra-layer snapping: pairwise snapping of adjacent polygons
        geoms = list(result_gdf.geometry)
        n = len(geoms)
        for i in range(n):
            if geoms[i] is None or geoms[i].is_empty:
                continue
            # Snap against other polygons within bounding box buffer
            for j in range(n):
                if i == j or geoms[j] is None or geoms[j].is_empty:
                    continue
                if geoms[i].distance(geoms[j]) <= tolerance:
                    snapped_geom, v_count = snap_geometry_to_reference(geoms[i], geoms[j], tolerance=tolerance)
                    if not geoms[i].equals_exact(snapped_geom, 1e-12):
                        geoms[i] = snapped_geom
                        feat_id = result_gdf.iloc[i].get("feature_id", str(i))
                        fixes.append(
                            TopologyFixEvent(
                                fix_type="snap",
                                feature_index=i,
                                feature_id=str(feat_id),
                                description=f"Intra-layer vertex snap with neighboring polygon {j}",
                                vertices_affected=max(1, v_count),
                            )
                        )
        result_gdf["geometry"] = geoms

    return result_gdf, fixes


def detect_overlaps(
    gdf: gpd.GeoDataFrame,
    min_overlap_sqm: float = 0.01,
) -> list[dict[str, Any]]:
    """Detect overlapping polygons within a single layer or dataset."""
    overlaps = []
    if gdf.empty or len(gdf) < 2:
        return overlaps

    geoms = list(gdf.geometry)
    n = len(geoms)
    for i in range(n):
        g1 = geoms[i]
        if g1 is None or g1.is_empty:
            continue
        for j in range(i + 1, n):
            g2 = geoms[j]
            if g2 is None or g2.is_empty:
                continue
            if g1.intersects(g2):
                try:
                    inter = g1.intersection(g2)
                    if inter is not None and not inter.is_empty and inter.area > 0:
                        area_sqm = _approx_deg_to_sqm(inter.area)
                        if area_sqm >= min_overlap_sqm:
                            f1_id = gdf.iloc[i].get("feature_id", str(i))
                            f2_id = gdf.iloc[j].get("feature_id", str(j))
                            overlaps.append({
                                "index_a": i,
                                "index_b": j,
                                "feature_a": str(f1_id),
                                "feature_b": str(f2_id),
                                "overlap_area_sqm": round(area_sqm, 4),
                                "overlap_geojson": mapping(inter),
                            })
                except Exception:
                    continue
    return overlaps


def detect_gaps_and_slivers(
    gdf: gpd.GeoDataFrame,
    max_gap_area_sqm: float = 50.0,
    snap_tolerance: float = 0.00005,
) -> list[dict[str, Any]]:
    """Detect micro-gaps (vacant sliver holes between adjacent parcels).

    Calculates internal holes in the unary union of all parcel geometries
    that have area <= max_gap_area_sqm.
    """
    gaps = []
    if gdf.empty or len(gdf) < 2:
        return gaps

    valid_geoms = [g for g in gdf.geometry if g is not None and not g.is_empty and g.is_valid]
    if len(valid_geoms) < 2:
        return gaps

    try:
        union_geom = unary_union(valid_geoms)
        # Find internal holes
        polys = [union_geom] if union_geom.geom_type == "Polygon" else (
            list(union_geom.geoms) if union_geom.geom_type == "MultiPolygon" else []
        )

        for poly in polys:
            if not hasattr(poly, "interiors"):
                continue
            for interior in poly.interiors:
                hole_poly = Polygon(interior)
                hole_area_sqm = _approx_deg_to_sqm(hole_poly.area)
                if 0.001 <= hole_area_sqm <= max_gap_area_sqm:
                    gaps.append({
                        "gap_area_sqm": round(hole_area_sqm, 4),
                        "geometry": hole_poly,
                        "geojson": mapping(hole_poly),
                    })
    except Exception:
        pass

    return gaps


def resolve_overlaps(
    gdf: gpd.GeoDataFrame,
    max_overlap_area_sqm: float = 100.0,
) -> tuple[gpd.GeoDataFrame, list[TopologyFixEvent], int]:
    """Resolve micro-overlaps between polygons.

    Policy:
      - If overlap is <= max_overlap_area_sqm:
        The polygon with higher index (or lower area / secondary source) subtracts
        the overlap geometry from itself so boundaries become contiguous.
    """
    if gdf.empty or len(gdf) < 2:
        return gdf.copy(), [], 0

    result_gdf = gdf.copy()
    geoms = list(result_gdf.geometry)
    n = len(geoms)
    fixes: list[TopologyFixEvent] = []
    overlaps_resolved = 0

    for i in range(n):
        if geoms[i] is None or geoms[i].is_empty:
            continue
        for j in range(i + 1, n):
            if geoms[j] is None or geoms[j].is_empty:
                continue

            if geoms[i].intersects(geoms[j]):
                try:
                    inter = geoms[i].intersection(geoms[j])
                    if inter is not None and not inter.is_empty and inter.area > 0:
                        overlap_sqm = _approx_deg_to_sqm(inter.area)
                        if overlap_sqm <= max_overlap_area_sqm:
                            # Subtract overlap from geometry j
                            diff = geoms[j].difference(inter)
                            if not diff.is_empty and diff.is_valid:
                                geoms[j] = diff
                                overlaps_resolved += 1
                                f_id = result_gdf.iloc[j].get("feature_id", str(j))
                                fixes.append(
                                    TopologyFixEvent(
                                        fix_type="overlap_merge",
                                        feature_index=j,
                                        feature_id=str(f_id),
                                        description=f"Clipped {overlap_sqm:.2f} m² overlap with feature {result_gdf.iloc[i].get('feature_id', str(i))}",
                                        delta_area_sqm=round(overlap_sqm, 4),
                                    )
                                )
                except Exception:
                    continue

    result_gdf["geometry"] = geoms
    return result_gdf, fixes, overlaps_resolved


def resolve_gaps(
    gdf: gpd.GeoDataFrame,
    max_gap_area_sqm: float = 50.0,
    tolerance: float = 0.00005,
) -> tuple[gpd.GeoDataFrame, list[TopologyFixEvent], int]:
    """Resolve micro gaps by buffering/closing slivers into adjacent polygons."""
    gaps = detect_gaps_and_slivers(gdf, max_gap_area_sqm=max_gap_area_sqm, snap_tolerance=tolerance)
    if not gaps:
        return gdf.copy(), [], 0

    result_gdf = gdf.copy()
    geoms = list(result_gdf.geometry)
    fixes: list[TopologyFixEvent] = []
    gaps_resolved = 0

    for gap_info in gaps:
        gap_geom = gap_info["geometry"]
        gap_sqm = gap_info["gap_area_sqm"]

        # Find adjacent polygon with longest shared boundary / closest contact
        best_idx = None
        best_contact = 0.0

        for idx, g in enumerate(geoms):
            if g is None or g.is_empty:
                continue
            if g.touches(gap_geom) or g.distance(gap_geom) <= tolerance:
                # Union gap to this polygon
                try:
                    contact_len = g.intersection(gap_geom.buffer(1e-7)).length
                    if contact_len > best_contact or best_idx is None:
                        best_contact = contact_len
                        best_idx = idx
                except Exception:
                    best_idx = idx

        if best_idx is not None:
            try:
                merged = unary_union([geoms[best_idx], gap_geom])
                if not merged.is_valid:
                    merged = make_valid(merged)
                geoms[best_idx] = merged
                gaps_resolved += 1
                f_id = result_gdf.iloc[best_idx].get("feature_id", str(best_idx))
                fixes.append(
                    TopologyFixEvent(
                        fix_type="gap_fill",
                        feature_index=best_idx,
                        feature_id=str(f_id),
                        description=f"Absorbed {gap_sqm:.2f} m² vacant sliver gap",
                        delta_area_sqm=round(gap_sqm, 4),
                    )
                )
            except Exception:
                pass

    result_gdf["geometry"] = geoms
    return result_gdf, fixes, gaps_resolved


def correct_topology(
    gdf: gpd.GeoDataFrame,
    reference_gdf: gpd.GeoDataFrame | None = None,
    tolerance: float = 0.00005,
    max_gap_area_sqm: float = 50.0,
    max_overlap_area_sqm: float = 100.0,
    auto_merge_overlaps: bool = True,
    auto_fill_gaps: bool = True,
) -> tuple[gpd.GeoDataFrame, TopologyHealthReport]:
    """Automated Topology Correction Pipeline & Health Report Generator.

    Steps:
      1. Pre-correction audit (counts, initial validity, initial overlaps, initial gaps).
      2. In-place geometry validation repair (make_valid on self-intersections).
      3. Multi-layer & Intra-layer Vertex Snapping within tolerance.
      4. Overlap resolution (clipping micro-overlaps).
      5. Gap / vacant sliver absorption.
      6. Post-correction audit & Topology Health Report compilation.

    Returns:
        (corrected_gdf, health_report)
    """
    if gdf.empty:
        empty_report = TopologyHealthReport(status="clean", snap_tolerance=tolerance)
        return gdf.copy(), empty_report

    initial_features = len(gdf)
    all_fixes: list[TopologyFixEvent] = []

    # 1. Pre-audit
    initial_invalid = 0
    for idx, geom in enumerate(gdf.geometry):
        if geom is None or geom.is_empty or not geom.is_valid:
            initial_invalid += 1

    pre_overlaps = detect_overlaps(gdf)
    pre_overlap_area = sum(o["overlap_area_sqm"] for o in pre_overlaps)
    pre_gaps = detect_gaps_and_slivers(gdf, max_gap_area_sqm=max_gap_area_sqm, snap_tolerance=tolerance)
    pre_gap_area = sum(g["gap_area_sqm"] for g in pre_gaps)

    current_gdf = gdf.copy()

    # 2. Fix self-intersections (make_valid)
    valid_geoms = []
    for idx, row in current_gdf.iterrows():
        geom = row.geometry
        if geom is not None and not geom.is_empty and not geom.is_valid:
            fixed = make_valid(geom)
            valid_geoms.append(fixed)
            f_id = row.get("feature_id", str(idx))
            all_fixes.append(
                TopologyFixEvent(
                    fix_type="make_valid",
                    feature_index=int(idx) if isinstance(idx, (int, np.integer)) else None,
                    feature_id=str(f_id),
                    description="Repaired self-intersection / invalid ring via make_valid",
                )
            )
        else:
            valid_geoms.append(geom)
    current_gdf["geometry"] = valid_geoms

    # 3. Vertex Snapping (Multi-layer if reference_gdf provided, else intra-layer)
    current_gdf, snap_fixes = snap_layers(current_gdf, reference_gdf=reference_gdf, tolerance=tolerance)
    all_fixes.extend(snap_fixes)

    # If reference was provided, also do light intra-layer snap to ensure neighbor topology is closed
    if reference_gdf is not None:
        current_gdf, intra_fixes = snap_layers(current_gdf, reference_gdf=None, tolerance=tolerance)
        all_fixes.extend(intra_fixes)

    # 4. Overlap resolution
    overlaps_resolved = 0
    if auto_merge_overlaps:
        current_gdf, overlap_fixes, overlaps_resolved = resolve_overlaps(
            current_gdf, max_overlap_area_sqm=max_overlap_area_sqm
        )
        all_fixes.extend(overlap_fixes)

    # 5. Gap resolution
    gaps_resolved = 0
    if auto_fill_gaps:
        current_gdf, gap_fixes, gaps_resolved = resolve_gaps(
            current_gdf, max_gap_area_sqm=max_gap_area_sqm, tolerance=tolerance
        )
        all_fixes.extend(gap_fixes)

    # 6. Post-audit metrics
    post_invalid = 0
    for geom in current_gdf.geometry:
        if geom is None or geom.is_empty or not geom.is_valid:
            post_invalid += 1

    post_overlaps = detect_overlaps(current_gdf)
    post_overlap_area = sum(o["overlap_area_sqm"] for o in post_overlaps)
    post_gaps = detect_gaps_and_slivers(current_gdf, max_gap_area_sqm=max_gap_area_sqm, snap_tolerance=tolerance)
    post_gap_area = sum(g["gap_area_sqm"] for g in post_gaps)

    vertices_snapped_total = sum(f.vertices_affected for f in all_fixes if f.fix_type == "snap")
    slivers_cleaned_total = len([f for f in all_fixes if f.fix_type in ("gap_fill", "overlap_merge")])

    # Composite health score (0 - 100):
    # Penalize remaining invalid geoms (30%), overlaps (40%), and gaps (30%)
    invalid_penalty = (post_invalid / max(1, initial_features)) * 30.0
    overlap_penalty = min(40.0, len(post_overlaps) * 10.0 + (post_overlap_area / 100.0) * 10.0)
    gap_penalty = min(30.0, len(post_gaps) * 10.0 + (post_gap_area / 100.0) * 10.0)
    final_score = max(0.0, min(100.0, round(100.0 - invalid_penalty - overlap_penalty - gap_penalty, 1)))

    init_invalid_pen = (initial_invalid / max(1, initial_features)) * 30.0
    init_ov_pen = min(40.0, len(pre_overlaps) * 10.0 + (pre_overlap_area / 100.0) * 10.0)
    init_gap_pen = min(30.0, len(pre_gaps) * 10.0 + (pre_gap_area / 100.0) * 10.0)
    initial_score = max(0.0, min(100.0, round(100.0 - init_invalid_pen - init_ov_pen - init_gap_pen, 1)))

    status = "clean" if (post_invalid == 0 and len(post_overlaps) == 0 and len(post_gaps) == 0) else (
        "corrected" if len(all_fixes) > 0 else "issues_remaining"
    )

    summary = TopologyMetricSummary(
        total_features=initial_features,
        valid_features=initial_features - post_invalid,
        invalid_features=post_invalid,
        overlaps_detected=len(pre_overlaps),
        overlaps_resolved=overlaps_resolved,
        gaps_detected=len(pre_gaps),
        gaps_resolved=gaps_resolved,
        vertices_snapped=vertices_snapped_total,
        slivers_cleaned=slivers_cleaned_total,
        total_overlap_area_sqm=round(post_overlap_area, 4),
        total_gap_area_sqm=round(post_gap_area, 4),
        initial_health_score=initial_score,
        final_health_score=final_score,
    )

    fix_dicts = [asdict(f) for f in all_fixes]
    issue_dicts = [
        {"type": "overlap", "description": f"Remaining overlap between {o['feature_a']} and {o['feature_b']}", "area_sqm": o["overlap_area_sqm"]}
        for o in post_overlaps
    ] + [
        {"type": "gap", "description": f"Remaining vacant sliver hole of {g['gap_area_sqm']} m²", "area_sqm": g["gap_area_sqm"]}
        for g in post_gaps
    ]

    report = TopologyHealthReport(
        status=status,
        summary=summary,
        fixes=fix_dicts,
        issues=issue_dicts,
        snap_tolerance=tolerance,
        area_tolerance_sqm=max_gap_area_sqm,
    )

    return current_gdf, report
