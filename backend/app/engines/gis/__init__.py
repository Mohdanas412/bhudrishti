"""
GIS engine — owner M4.

Pipeline: ingestion -> validation -> normalization -> spatial_index -> candidate_generation -> topology
"""

from app.engines.gis.ingestion import IngestError, IngestResult, ingest_dataset
from app.engines.gis.topology import (
    TopologyFixEvent,
    TopologyHealthReport,
    TopologyMetricSummary,
    correct_topology,
    detect_gaps_and_slivers,
    detect_overlaps,
    resolve_gaps,
    resolve_overlaps,
    snap_geometry_to_reference,
    snap_layers,
)
from app.engines.gis.validation import (
    IssueCode,
    RepairResult,
    ValidationResult,
    repair_dataset,
    validate_dataset,
)

__all__ = [
    "IngestError",
    "IngestResult",
    "IssueCode",
    "RepairResult",
    "TopologyFixEvent",
    "TopologyHealthReport",
    "TopologyMetricSummary",
    "ValidationResult",
    "correct_topology",
    "detect_gaps_and_slivers",
    "detect_overlaps",
    "ingest_dataset",
    "repair_dataset",
    "resolve_gaps",
    "resolve_overlaps",
    "snap_geometry_to_reference",
    "snap_layers",
    "validate_dataset",
]
