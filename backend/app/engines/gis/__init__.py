"""
GIS engine — owner M4.

Pipeline: ingestion -> validation -> normalization -> spatial_index -> candidate_generation
See README.md in this folder for the per-file contract.
"""

from app.engines.gis.ingestion import IngestError, IngestResult, ingest_dataset
from app.engines.gis.validation import IssueCode, ValidationResult, validate_dataset

__all__ = [
    "IngestError",
    "IngestResult",
    "IssueCode",
    "ValidationResult",
    "ingest_dataset",
    "validate_dataset",
]
