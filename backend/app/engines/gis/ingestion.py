"""
GIS ingestion — owner M4.

Stage 1 of the GIS pipeline (playbook Section 6):
    ingestion -> validation -> normalization -> spatial_index -> candidate_generation

Responsibilities (this module only):
  1. Read a geospatial file (GeoJSON / Shapefile / GPKG) from disk.
  2. Detect its CRS. Raise if missing — silent defaulting hides real data bugs.
  3. Reproject to EPSG:4326, the canonical target (matches schema.sql
     features.geometry(Geometry, 4326) and datasets.coverage_boundary(Polygon, 4326)).
  4. Compute a single coverage_boundary polygon as the union of per-feature
     convex hulls. This is the dataset extent used by the coverage-aware
     missing-feature rule (Addendum Critical Fix 4).

Hard rules (playbook Section 10 + engines/gis/README):
  * This module is storage-agnostic. No imports from app.db.* or app.models.*.
    The service layer is responsible for persisting IngestResult.
  * Never mutate the original uploaded file. We read into a GeoDataFrame and
    operate on that in-memory copy only.
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
from shapely.geometry import mapping
from shapely.ops import unary_union

# Canonical CRS for the whole BhuDrishti pipeline.
TARGET_CRS = "EPSG:4326"


class IngestError(Exception):
    """Raised when a dataset cannot be ingested (e.g. missing CRS, unreadable file)."""


@dataclass
class IngestResult:
    """Outcome of ingesting one dataset file. Storage-agnostic."""

    gdf: gpd.GeoDataFrame
    crs: str  # always TARGET_CRS on success
    feature_count: int
    coverage_geojson: dict  # GeoJSON Polygon or MultiPolygon


def ingest_dataset(file_path: str) -> IngestResult:
    """Read, CRS-normalize, and compute coverage for one uploaded dataset.

    Args:
        file_path: absolute or backend-relative path to a geospatial file
                   readable by geopandas (GeoJSON, Shapefile, GPKG, ...).

    Returns:
        IngestResult with the reprojected GeoDataFrame and the coverage
        boundary as a GeoJSON dict ready to be JSON-serialized into the
        Dataset.coverage_boundary_geojson column.

    Raises:
        IngestError: file unreadable, CRS missing, or no valid geometries.
    """
    try:
        gdf = gpd.read_file(file_path)
    except Exception as exc:  # geopandas/fiona raise a wide variety of types
        raise IngestError(f"Failed to read geospatial file '{file_path}': {exc}") from exc

    if gdf.empty:
        raise IngestError(f"Dataset '{file_path}' contains no features")

    if gdf.crs is None:
        # Surface the error rather than silently defaulting to 4326.
        # Municipal / survey data shipped without CRS is a real data-quality
        # signal that the uploader should fix upstream.
        raise IngestError(
            "CRS missing — cannot normalize. "
            "Re-export the source file with a 'crs' member (e.g. EPSG:4326 or EPSG:32643)."
        )

    # Reproject to canonical CRS. GeoPandas' to_crs is a no-op when already
    # in the target CRS, so this also covers the WGS84 passthrough case.
    normalized = gdf.to_crs(TARGET_CRS)

    coverage_geojson = _compute_coverage(normalized)

    return IngestResult(
        gdf=normalized,
        crs=TARGET_CRS,
        feature_count=len(normalized),
        coverage_geojson=coverage_geojson,
    )


def _compute_coverage(gdf: gpd.GeoDataFrame) -> dict:
    """Union of per-feature convex hulls, serialized as GeoJSON.

    convex_hull is the cheap standard approximation for a dataset's
    extent. If M5 needs a tighter boundary later (e.g. concave_hull),
    swap it in here — callers only see the GeoJSON.
    """
    # Drop null/empty geoms first so unary_union doesn't choke.
    valid_geoms = [geom for geom in gdf.geometry if geom is not None and not geom.is_empty]
    if not valid_geoms:
        raise IngestError("Dataset has no non-empty geometries; cannot compute coverage")

    hulls = [geom.convex_hull for geom in valid_geoms]
    coverage = unary_union(hulls)
    return mapping(coverage)
