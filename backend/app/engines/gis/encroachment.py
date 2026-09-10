"""
GeoAI Spatial Encroachment, Buffer Breach & Change Detection Engine.

Analyzes intersection deltas between Survey / Drone / Footprint imagery
and Cadastral land parcel records to identify illegal encroachments, slivers,
and Right-of-Way (RoW) buffer zone incursions based on permissible variance thresholds.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

import geopandas as gpd
from shapely.geometry import mapping
from shapely.validation import make_valid


@dataclass
class EncroachmentMetrics:
    """Quantitative metrics and GeoJSON geometry for a detected encroachment."""

    encroachment_id: str
    feature_id_cadastral: str
    feature_id_drone: str
    intersection_area_sqm: float
    encroachment_area_sqm: float
    variance_percentage: float
    status: str  # 'permissible', 'flagged'
    severity: str = "medium"  # 'low', 'medium', 'high', 'critical'
    geometry: dict[str, Any] | None = None  # GeoJSON dict of encroachment polygon

    def to_geojson_feature(self) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": self.encroachment_id,
            "geometry": self.geometry,
            "properties": {
                "encroachment_id": self.encroachment_id,
                "feature_id_cadastral": self.feature_id_cadastral,
                "feature_id_drone": self.feature_id_drone,
                "intersection_area_sqm": self.intersection_area_sqm,
                "encroachment_area_sqm": self.encroachment_area_sqm,
                "variance_percentage": self.variance_percentage,
                "status": self.status,
                "severity": self.severity,
                "feature_type": "encroachment_polygon",
            },
        }


@dataclass
class EncroachmentReport:
    """Report summarizing all detected encroachments in a dataset with GeoJSON output."""

    total_encroachments: int
    total_area_sqm: float
    metrics: list[EncroachmentMetrics] = field(default_factory=list)
    geojson_features: list[dict[str, Any]] = field(default_factory=list)
    row_buffer_breaches: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_encroachments": self.total_encroachments,
            "total_area_sqm": round(self.total_area_sqm, 2),
            "metrics": [asdict(m) for m in self.metrics],
            "geojson": {
                "type": "FeatureCollection",
                "features": self.geojson_features,
            },
            "row_buffer_breaches": self.row_buffer_breaches,
        }


def _calculate_area_sqm(geom: Any) -> float:
    """Accurately calculates area in square meters for either geographic or projected geometries."""
    if geom is None or geom.is_empty:
        return 0.0

    bounds = geom.bounds  # minx, miny, maxx, maxy
    # Check if coordinates are in geographic degrees (WGS84)
    is_degrees = (-180.0 <= bounds[0] <= 180.0) and (-90.0 <= bounds[1] <= 90.0) and (abs(bounds[2] - bounds[0]) < 10.0)

    if is_degrees:
        mean_lat = (bounds[1] + bounds[3]) / 2.0
        # 1 degree latitude ~ 111,000 meters; 1 degree longitude ~ 111,000 * cos(lat) meters
        lat_m = 111000.0
        lon_m = 111000.0 * math.cos(math.radians(mean_lat))
        return float(geom.area * lat_m * lon_m)
    else:
        # Already in projected meters (e.g. UTM)
        return float(geom.area)


def detect_encroachments(
    cadastral_gdf: gpd.GeoDataFrame,
    drone_gdf: gpd.GeoDataFrame,
    permissible_variance_sqm: float = 5.0,
) -> EncroachmentReport:
    """Analyzes spatial delta between Drone (Survey) and Cadastral (Legal) plots.

    1. Intersects drone footprints with cadastral parcels.
    2. Calculates area extending outside legal cadastral boundary.
    3. Emits validated GeoJSON features and classification.
    """
    if cadastral_gdf.empty or drone_gdf.empty:
        return EncroachmentReport(0, 0.0, [], [], [])

    # Spatial join to identify candidate overlapping parcels
    try:
        join_gdf = gpd.sjoin(drone_gdf, cadastral_gdf, how="inner", predicate="intersects")
    except Exception:
        # Fallback if CRS mismatch or unindexed
        join_gdf = gpd.GeoDataFrame()

    metrics: list[EncroachmentMetrics] = []
    geojson_features: list[dict[str, Any]] = []
    total_area = 0.0

    # Iterate candidate overlaps
    for row_idx, row in join_gdf.iterrows():
        geom_drone = row.geometry
        cadastral_idx = row.get("index_right")
        if cadastral_idx is None or cadastral_idx not in cadastral_gdf.index:
            continue

        geom_cadastral = cadastral_gdf.loc[cadastral_idx, "geometry"]
        if geom_drone is None or geom_cadastral is None:
            continue

        if not geom_drone.is_valid:
            geom_drone = make_valid(geom_drone)
        if not geom_cadastral.is_valid:
            geom_cadastral = make_valid(geom_cadastral)

        try:
            intersection = geom_drone.intersection(geom_cadastral)
            encroachment_geom = geom_drone.difference(geom_cadastral)
        except Exception:
            continue

        if encroachment_geom.is_empty:
            continue

        enc_area = _calculate_area_sqm(encroachment_geom)
        inter_area = _calculate_area_sqm(intersection)
        cad_area = _calculate_area_sqm(geom_cadastral)

        if enc_area > 0.01:
            status = "permissible" if enc_area <= permissible_variance_sqm else "flagged"

            if enc_area > 50.0:
                severity = "critical"
            elif enc_area > 20.0:
                severity = "high"
            elif status == "flagged":
                severity = "medium"
            else:
                severity = "low"

            cad_id = str(cadastral_gdf.loc[cadastral_idx].get("feature_id", cadastral_idx))
            drone_id = str(row.get("feature_id", row_idx))

            metric = EncroachmentMetrics(
                encroachment_id=f"ENC-{row_idx}-{cadastral_idx}",
                feature_id_cadastral=cad_id,
                feature_id_drone=drone_id,
                intersection_area_sqm=round(inter_area, 2),
                encroachment_area_sqm=round(enc_area, 2),
                variance_percentage=round((enc_area / max(cad_area, 1e-6)) * 100.0, 2),
                status=status,
                severity=severity,
                geometry=mapping(encroachment_geom),
            )
            metrics.append(metric)
            geojson_features.append(metric.to_geojson_feature())

            if status == "flagged":
                total_area += enc_area

    flagged_count = len([m for m in metrics if m.status == "flagged"])

    return EncroachmentReport(
        total_encroachments=flagged_count,
        total_area_sqm=round(total_area, 2),
        metrics=metrics,
        geojson_features=geojson_features,
    )


def detect_row_buffer_breaches(
    corridor_gdf: gpd.GeoDataFrame,
    parcels_gdf: gpd.GeoDataFrame,
    buffer_meters: float = 10.0,
) -> list[dict[str, Any]]:
    """Detects parcels or structures violating Right-of-Way (RoW) buffer zones."""
    breaches = []
    if corridor_gdf.empty or parcels_gdf.empty:
        return breaches

    # Buffer conversion: ~10m in degrees is roughly 0.00009 deg
    buffer_deg = buffer_meters / 111000.0

    for c_idx, c_row in corridor_gdf.iterrows():
        c_geom = c_row.geometry
        if c_geom is None or c_geom.is_empty:
            continue

        try:
            buffered_corridor = c_geom.buffer(buffer_deg)
            for p_idx, p_row in parcels_gdf.iterrows():
                p_geom = p_row.geometry
                if p_geom is None or p_geom.is_empty:
                    continue
                if buffered_corridor.intersects(p_geom):
                    breach_geom = buffered_corridor.intersection(p_geom)
                    if not breach_geom.is_empty and breach_geom.area > 0:
                        breach_area = _calculate_area_sqm(breach_geom)
                        breaches.append({
                            "breach_id": f"ROW-{c_idx}-{p_idx}",
                            "corridor_feature": str(c_row.get("feature_id", c_idx)),
                            "parcel_feature": str(p_row.get("feature_id", p_idx)),
                            "buffer_meters": buffer_meters,
                            "breach_area_sqm": round(breach_area, 2),
                            "geometry": mapping(breach_geom),
                        })
        except Exception:
            continue

    return breaches
