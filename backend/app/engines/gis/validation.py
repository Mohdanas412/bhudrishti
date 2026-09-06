"""
GIS validation — owner M4.

Stage 2 of the GIS pipeline (playbook Section 6):
    ingestion -> validation -> normalization -> spatial_index -> candidate_generation

Responsibilities (this module only):
  1. Run per-feature geometry checks (empty, invalid) on a dataset.
  2. Map whole-file failures (missing CRS, unreadable file) into the same
     issue shape so the API consumer has one schema to handle.
  3. Return a structured ValidationResult the service layer can persist.
  4. Optionally repair invalid geometries in-place (shapely.make_valid),
     dropping those that cannot be repaired, and return the cleaned GDF
     alongside the report.

This module reuses `ingest_dataset()` for the read+CRS-normalize step so
CRS detection logic stays in one place. We do NOT re-read the file —
the in-memory GeoDataFrame from `ingest_dataset` is the working copy.

Hard rules (playbook Section 10 + engines/gis/README):
  * Storage-agnostic. No imports from app.db.* or app.models.*.
  * Never mutate the source file. Operate on the in-memory GeoDataFrame only.
  * Issue codes are stable strings the API/tests can branch on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import geopandas as gpd
from shapely.validation import make_valid

from app.engines.gis.ingestion import IngestError, ingest_dataset


class IssueCode:
    """Stable string codes for validation issues.

    Kept as plain string constants (not an enum) so they serialize cleanly
    to JSON without a custom encoder. Frontend / M5 can `==` against these.
    """

    EMPTY_GEOMETRY = "empty_geometry"
    INVALID_GEOMETRY = "invalid_geometry"
    CRS_MISSING = "crs_missing"
    FILE_UNREADABLE = "file_unreadable"
    UNREPAIRABLE_GEOMETRY = "unrepairable_geometry"


@dataclass
class ValidationResult:
    """Outcome of validating one dataset file. Storage-agnostic."""

    valid: bool
    issues: list[dict] = field(default_factory=list)
    # CRS of the source file. None when the file has no CRS info (which
    # the previous M3 code also stored as the string "None" — we use
    # Python None for clarity and let the service decide how to persist).
    crs: str | None = None
    feature_count: int = 0


@dataclass
class RepairResult:
    """Outcome of repairing one dataset file. Storage-agnostic.

    `gdf` contains only the features that survived repair (invalid-but-fixable
    geoms have been replaced via shapely.make_valid; empty/unfixable geoms
    have been dropped). `issues` covers the final disposition per dropped
    feature, with the original feature_index for traceability.
    """

    gdf: gpd.GeoDataFrame
    crs: str | None
    feature_count: int  # features kept after drops
    dropped_count: int  # features removed
    issues: list[dict] = field(default_factory=list)
    # Original feature_index values for geoms that were repaired in-place.
    repaired_indices: list[int] = field(default_factory=list)


def validate_dataset(file_path: str) -> ValidationResult:
    """Validate a dataset file: per-feature geometry checks + file-level checks.

    Reuses `ingest_dataset()` so the read path and CRS detection are not
    duplicated. Whole-file failures (missing CRS, unreadable file) are
    mapped into the same `{feature_index, reason, code}` issue shape as
    per-feature failures, with `feature_index=None`.

    Args:
        file_path: path to a geospatial file readable by geopandas.

    Returns:
        ValidationResult. Always returns; never raises. The `valid` flag
        tells the caller whether the dataset is usable downstream.
    """
    try:
        ingested = ingest_dataset(file_path)
    except IngestError as exc:
        message = str(exc)
        if "CRS missing" in message:
            return ValidationResult(
                valid=False,
                issues=[
                    {
                        "feature_index": None,
                        "reason": message,
                        "code": IssueCode.CRS_MISSING,
                    }
                ],
                crs=None,
                feature_count=0,
            )
        # Anything else from ingest = file unreadable / parse failure
        return ValidationResult(
            valid=False,
            issues=[
                {
                    "feature_index": None,
                    "reason": message,
                    "code": IssueCode.FILE_UNREADABLE,
                }
            ],
            crs=None,
            feature_count=0,
        )

    # Reached here: file was readable, CRS was present (otherwise IngestError).
    # We have a reprojected GeoDataFrame in ingested.gdf.
    gdf: gpd.GeoDataFrame = ingested.gdf

    issues: list[dict] = []
    for idx, geom in enumerate(gdf.geometry):
        if geom is None or geom.is_empty:
            issues.append(
                {
                    "feature_index": idx,
                    "reason": "Empty geometry",
                    "code": IssueCode.EMPTY_GEOMETRY,
                }
            )
        elif not geom.is_valid:
            issues.append(
                {
                    "feature_index": idx,
                    "reason": "Invalid geometry (e.g. self-intersection)",
                    "code": IssueCode.INVALID_GEOMETRY,
                }
            )

    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        crs=ingested.crs,
        feature_count=ingested.feature_count,
    )


def repair_dataset(file_path: str) -> RepairResult:
    """Repair a dataset file: fix self-intersections in-place, drop empty
    or unrepairable geometries, return the cleaned GeoDataFrame.

    Repair policy:
      * `None` or empty geometry  -> drop, emit UNREPAIRABLE_GEOMETRY
        with reason "Empty geometry".
      * Invalid (non-empty) geometry -> try shapely.make_valid. If the
        result is empty/None, drop + emit UNREPAIRABLE_GEOMETRY with
        reason "Geometry could not be made valid". Otherwise, replace
        in place and record the original feature_index in
        `repaired_indices`.
      * Already-valid geometry -> keep as-is.

    Whole-file failures (missing CRS, unreadable file) are mapped into
    the same `{feature_index: None, reason, code}` issue shape as
    `validate_dataset`, with an empty gdf and dropped_count=0 (we never
    read features for an unreadable file).

    Args:
        file_path: path to a geospatial file readable by geopandas.

    Returns:
        RepairResult. Always returns; never raises. The cleaned GDF is in
        EPSG:4326 and contains only valid, non-empty features.
    """
    # Step 1: load the GDF via the ingestion path. We duplicate the
    # IngestError handling here (rather than calling validate_dataset)
    # because we need the *raw* GeoDataFrame to operate on, not just
    # a ValidationResult. The error mapping, however, is identical.
    try:
        ingested = ingest_dataset(file_path)
    except IngestError as exc:
        message = str(exc)
        if "CRS missing" in message:
            return RepairResult(
                gdf=gpd.GeoDataFrame(),
                crs=None,
                feature_count=0,
                dropped_count=0,
                issues=[
                    {
                        "feature_index": None,
                        "reason": message,
                        "code": IssueCode.CRS_MISSING,
                    }
                ],
            )
        return RepairResult(
            gdf=gpd.GeoDataFrame(),
            crs=None,
            feature_count=0,
            dropped_count=0,
            issues=[
                {
                    "feature_index": None,
                    "reason": message,
                    "code": IssueCode.FILE_UNREADABLE,
                }
            ],
        )

    gdf: gpd.GeoDataFrame = ingested.gdf

    # Step 2: walk the geometry, building kept-rows and an issues list.
    keep_mask: list[bool] = []
    issues: list[dict] = []
    repaired_indices: list[int] = []
    fixed_geoms: list = []  # aligned with the kept rows

    for idx, geom in enumerate(gdf.geometry):
        if geom is None or geom.is_empty:
            keep_mask.append(False)
            issues.append(
                {
                    "feature_index": idx,
                    "reason": "Empty geometry",
                    "code": IssueCode.UNREPAIRABLE_GEOMETRY,
                }
            )
            continue

        if not geom.is_valid:
            fixed = make_valid(geom)
            if fixed is None or fixed.is_empty:
                keep_mask.append(False)
                issues.append(
                    {
                        "feature_index": idx,
                        "reason": "Geometry could not be made valid",
                        "code": IssueCode.UNREPAIRABLE_GEOMETRY,
                    }
                )
                continue
            keep_mask.append(True)
            fixed_geoms.append(fixed)
            repaired_indices.append(idx)
            continue

        # Already valid — keep as-is. We still need an entry in
        # fixed_geoms aligned with the kept rows.
        keep_mask.append(True)
        fixed_geoms.append(geom)

    # Step 3: build the cleaned GDF. The simplest correct path is to
    # reindex the original and overwrite the geometry column with our
    # potentially-replaced values. Preserves all non-geometry columns.
    cleaned = gdf.loc[keep_mask].copy()
    if not cleaned.empty:
        cleaned.loc[:, "geometry"] = fixed_geoms
        # GeoDataFrame geometry column sometimes needs a re-assign to
        # be recognised after in-place edit; explicit re-set is safe.
        cleaned = gpd.GeoDataFrame(cleaned, geometry="geometry", crs=ingested.crs)

    dropped_count = len(gdf) - len(cleaned)

    return RepairResult(
        gdf=cleaned,
        crs=ingested.crs,
        feature_count=len(cleaned),
        dropped_count=dropped_count,
        issues=issues,
        repaired_indices=repaired_indices,
    )
