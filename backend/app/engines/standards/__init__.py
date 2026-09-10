"""
Standards Engine — ULPIN (Bhu-Aadhar) Geohash & Indic NLP Mapper.
"""

from app.engines.standards.indic_nlp import (
    AREA_UNIT_CONVERSIONS_SQM,
    INDIC_FIELD_MAP,
    map_indic_properties,
    normalize_indic_key,
    parse_indic_area,
)
from app.engines.standards.ulpin import (
    assign_ulpins_to_gdf,
    decode_ulpin,
    generate_ulpin,
    validate_ulpin,
)

__all__ = [
    "AREA_UNIT_CONVERSIONS_SQM",
    "INDIC_FIELD_MAP",
    "assign_ulpins_to_gdf",
    "decode_ulpin",
    "generate_ulpin",
    "map_indic_properties",
    "normalize_indic_key",
    "parse_indic_area",
    "validate_ulpin",
]
