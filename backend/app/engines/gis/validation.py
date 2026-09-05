"""
GIS validation — owner M4.

Stage 2 of the GIS pipeline (playbook Section 6):
    ingestion -> validation -> normalization -> spatial_index -> candidate_generation

Responsibilities (this module only):
  1. Run per-feature geometry checks (empty, invalid) on a dataset.
  2. Map whole-file failures (missing CRS, unreadable file) into the same
     issue shape so the API consumer has one schema to handle.
  3. Return a structured ValidationResult the service layer can persist.

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
