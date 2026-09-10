"""
GIS ingestion engine for BhuDrishti.

Stage 1 of the GIS pipeline:
    ingestion -> validation -> normalization -> spatial_index -> candidate_generation

Features:
  1. Read multiple geospatial formats:
     - GeoJSON / JSON (RFC 7946 compliant)
     - Shapefiles (.shp, or zipped .zip archives)
     - KML / KMZ (via Fiona KML driver)
     - CSV / TSV / Excel (.xlsx, .xls) with coordinate detection (lat/lon/x/y/WKT)
  2. Detect CRS; reproject to canonical EPSG:4326.
  3. Coordinate Inversion Safeguard: Detect inverted lat/lon and fix them cleanly.
  4. Robust geometry fixing: Ensure valid geometries via shapely.validation.make_valid.
  5. Compute coverage boundary polygon (union of convex hulls).

Hard rules:
  * Storage-agnostic. No imports from app.db.* or app.models.*.
  * Never mutate the source file on disk.
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

# Canonical CRS for the whole BhuDrishti pipeline.
TARGET_CRS = "EPSG:4326"


class IngestError(Exception):
    """Raised when a dataset cannot be ingested."""


@dataclass
class IngestResult:
    """Outcome of ingesting one dataset file. Storage-agnostic."""

    gdf: gpd.GeoDataFrame
    crs: str  # always TARGET_CRS on success
    feature_count: int
    coverage_geojson: dict  # GeoJSON Polygon or MultiPolygon


def _fix_coordinate_inversion(geom: Any) -> Any:
    """Detects and fixes coordinate inversion (lat/lon swapped where lon < 90 and lat > 90)."""
    if geom is None or geom.is_empty:
        return geom

    # Check bounds (minx, miny, maxx, maxy)
    bounds = geom.bounds  # minx, miny, maxx, maxy
    # In WGS84: x is longitude [-180, 180], y is latitude [-90, 90].
    # Case 1: If y is outside [-90, 90] and x is inside [-90, 90], they are definitely swapped.
    if (bounds[1] < -90 or bounds[3] > 90) and (-90 <= bounds[0] <= 90 and -90 <= bounds[2] <= 90):
        from shapely.ops import transform
        return transform(lambda x, y, *args: (y, x), geom)

    # Case 2: Indian subcontinent extent heuristic:
    # Authoritative lon in [68, 98], lat in [6, 38]. If x in [6, 38] and y in [68, 98], they are swapped.
    if (6.0 <= bounds[0] <= 38.0 and 6.0 <= bounds[2] <= 38.0) and (68.0 <= bounds[1] <= 98.0 and 68.0 <= bounds[3] <= 98.0):
        from shapely.ops import transform
        return transform(lambda x, y, *args: (y, x), geom)

    return geom


def _read_tabular_coordinates(file_path: str) -> gpd.GeoDataFrame:
    """Reads CSV/Excel tabular files and detects spatial coordinate or WKT columns."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    elif ext in (".tsv",):
        df = pd.read_csv(file_path, sep="\t")
    else:
        df = pd.read_csv(file_path)

    if df.empty:
        raise IngestError(f"Tabular dataset '{file_path}' is empty")

    cols_lower = {str(col).strip().lower(): col for col in df.columns}

    # 1. Check for WKT geometry column
    wkt_col = None
    for cand in ["geometry", "wkt", "geom", "the_geom", "shape"]:
        if cand in cols_lower:
            wkt_col = cols_lower[cand]
            break

    if wkt_col:
        geoms = []
        for val in df[wkt_col]:
            if pd.isna(val) or not str(val).strip():
                geoms.append(None)
            else:
                try:
                    s_geom = wkt.loads(str(val).strip())
                    s_geom = _fix_coordinate_inversion(s_geom)
                    if not s_geom.is_valid:
                        s_geom = make_valid(s_geom)
                    geoms.append(s_geom)
                except Exception:
                    geoms.append(None)
        gdf = gpd.GeoDataFrame(df.drop(columns=[wkt_col]), geometry=geoms, crs=TARGET_CRS)
        return gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty]

    # 2. Check for Latitude / Longitude columns
    lat_col = None
    lon_col = None

    for cand in ["latitude", "lat", "y", "y_coord", "northing"]:
        if cand in cols_lower:
            lat_col = cols_lower[cand]
            break

    for cand in ["longitude", "lon", "long", "lng", "x", "x_coord", "easting"]:
        if cand in cols_lower:
            lon_col = cols_lower[cand]
            break

    if lat_col and lon_col:
        # Check for coordinate inversion in column data
        sample_lat = pd.to_numeric(df[lat_col], errors="coerce").dropna()
        sample_lon = pd.to_numeric(df[lon_col], errors="coerce").dropna()

        # If sample latitudes > 90 and sample longitudes <= 90, swap columns
        if not sample_lat.empty and not sample_lon.empty:
            if sample_lat.abs().max() > 90 and sample_lon.abs().max() <= 90:
                lat_col, lon_col = lon_col, lat_col

        x_pts = pd.to_numeric(df[lon_col], errors="coerce")
        y_pts = pd.to_numeric(df[lat_col], errors="coerce")
        geoms = [
            _fix_coordinate_inversion(Point(x, y)) if pd.notna(x) and pd.notna(y) else None
            for x, y in zip(x_pts, y_pts)
        ]
        gdf = gpd.GeoDataFrame(df, geometry=geoms, crs=TARGET_CRS)
        return gdf[gdf.geometry.notnull() & ~gdf.geometry.is_empty]

    raise IngestError(
        f"Tabular dataset '{file_path}' has no recognized coordinate columns "
        "(latitude/longitude, lat/lon, x/y) or WKT geometry column"
    )


def _read_kml_file(file_path: str) -> gpd.GeoDataFrame:
    """Reads KML files with enabled Fiona driver support."""
    try:
        import fiona.drvsupport
        fiona.drvsupport.supported_drivers["KML"] = "rw"
        fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
    except Exception:
        pass

    try:
        gdf = gpd.read_file(file_path, driver="KML")
        return gdf
    except Exception as exc:
        raise IngestError(f"Failed to parse KML file '{file_path}': {exc}") from exc


def ingest_dataset(file_path: str) -> IngestResult:
    """Read, CRS-normalize, and compute coverage for one uploaded dataset.

    Args:
        file_path: path to a geospatial file (GeoJSON, Shapefile, KML, CSV, Excel, Zip).

    Returns:
        IngestResult with the reprojected GeoDataFrame and the coverage boundary.

    Raises:
        IngestError: file unreadable, CRS missing, or no valid geometries.
    """
    if not os.path.exists(file_path):
        raise IngestError(f"Failed to read geospatial file '{file_path}': file does not exist")

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in (".csv", ".tsv", ".xlsx", ".xls"):
            gdf = _read_tabular_coordinates(file_path)
        elif ext in (".kml", ".kmz"):
            gdf = _read_kml_file(file_path)
        elif ext == ".zip":
            # Handle zipped shapefiles
            with zipfile.ZipFile(file_path, "r") as zf:
                shp_files = [f for f in zf.namelist() if f.lower().endswith(".shp")]
                if shp_files:
                    gdf = gpd.read_file(f"zip://{file_path}!{shp_files[0]}")
                else:
                    gdf = gpd.read_file(file_path)
        else:
            gdf = gpd.read_file(file_path)
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError(f"Failed to read geospatial file '{file_path}': {exc}") from exc

    if gdf.empty:
        raise IngestError(f"Dataset '{file_path}' contains no features")

    if gdf.crs is None:
        # If CRS is missing from raw file, raise error per canonical validation rule
        raise IngestError(
            "CRS missing — cannot normalize. "
            "Re-export the source file with a 'crs' member (e.g. EPSG:4326 or EPSG:32643)."
        )

    # Reproject to canonical CRS EPSG:4326
    normalized = gdf.to_crs(TARGET_CRS)

    # Coordinate inversion check (preserving raw geometries for validation and repair engines)
    fixed_geoms = []
    for geom in normalized.geometry:
        if geom is None or geom.is_empty:
            fixed_geoms.append(geom)
            continue
        g_fixed = _fix_coordinate_inversion(geom)
        fixed_geoms.append(g_fixed)

    normalized.geometry = fixed_geoms

    coverage_geojson = _compute_coverage(normalized)

    return IngestResult(
        gdf=normalized,
        crs=TARGET_CRS,
        feature_count=len(normalized),
        coverage_geojson=coverage_geojson,
    )


def _compute_coverage(gdf: gpd.GeoDataFrame) -> dict:
    """Union of per-feature convex hulls, serialized as GeoJSON."""
    valid_geoms = [geom for geom in gdf.geometry if geom is not None and not geom.is_empty]
    if not valid_geoms:
        raise IngestError("Dataset has no non-empty geometries; cannot compute coverage")

    hulls = [geom.convex_hull for geom in valid_geoms]
    coverage = unary_union(hulls)
    return mapping(coverage)
