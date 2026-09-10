"""
Standards & National Spatial Specs API Router.

Exposes:
  - ULPIN (Bhu-Aadhar) Geohash generation, validation, and decoding.
  - Indic / Vernacular Land Records NLP property mapping and area normalization.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.engines.standards import (
    AREA_UNIT_CONVERSIONS_SQM,
    decode_ulpin,
    generate_ulpin,
    map_indic_properties,
    parse_indic_area,
    validate_ulpin,
)

router = APIRouter()


class UlpinGenerateRequest(BaseModel):
    latitude: float = Field(..., description="WGS84 centroid latitude")
    longitude: float = Field(..., description="WGS84 centroid longitude")
    geometry: dict[str, Any] | None = Field(None, description="Optional GeoJSON Polygon geometry")


class UlpinValidateRequest(BaseModel):
    ulpin: str = Field(..., description="14-character ULPIN / Bhu-Aadhar string")


class IndicNlpMapRequest(BaseModel):
    properties: dict[str, Any] = Field(..., description="Dictionary containing vernacular Hindi / Indic keys")
    state_context: str = Field("NATIONAL", description="Regional revenue context")


class IndicAreaConvertRequest(BaseModel):
    raw_area: str = Field(..., description="Raw area string (e.g. '2 Bigha 5 Biswa', '4.5 Guntha')")


@router.post("/ulpin/generate")
async def generate_ulpin_endpoint(req: UlpinGenerateRequest):
    """Generate a 14-digit/character ULPIN / Bhu-Aadhar geohash (NAKSHA specification)."""
    try:
        ulpin_id = generate_ulpin(req.latitude, req.longitude, polygon=req.geometry)
        decoded = decode_ulpin(ulpin_id)
        return {
            "ulpin": ulpin_id,
            "bhu_aadhar": ulpin_id,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "bounding_box": decoded.get("bounding_box"),
            "valid": decoded.get("valid", True),
            "standard": "NAKSHA / DoLR DILRMP 14-character Geohash",
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"ULPIN generation failed: {exc!s}")


@router.post("/ulpin/decode")
async def decode_ulpin_endpoint(req: UlpinValidateRequest):
    """Decode a 14-character ULPIN into coordinate bounding box and verify check character."""
    try:
        res = decode_ulpin(req.ulpin)
        return res
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid ULPIN: {exc!s}")


@router.post("/ulpin/validate")
async def validate_ulpin_endpoint(req: UlpinValidateRequest):
    """Validate 14-digit/char ULPIN formatting and checksum."""
    is_valid = validate_ulpin(req.ulpin)
    return {"ulpin": req.ulpin, "valid": is_valid}


@router.post("/indic-nlp/map")
async def map_indic_properties_endpoint(req: IndicNlpMapRequest):
    """Translate and map Hindi/vernacular revenue fields into BhuDrishti canonical schema."""
    try:
        res = map_indic_properties(req.properties, state_context=req.state_context)
        return {
            "canonical": res,
            "source_properties": req.properties,
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Indic NLP mapping failed: {exc!s}")


@router.post("/indic-nlp/convert-area")
async def convert_indic_area_endpoint(req: IndicAreaConvertRequest):
    """Convert regional land area representation (Bigha, Biswa, Guntha, Kanal, Marla, Cent) into m² & hectares."""
    area_sqm, detected_unit = parse_indic_area(req.raw_area)
    if area_sqm is None:
        raise HTTPException(status_code=422, detail=f"Could not parse area from '{req.raw_area}'")

    return {
        "raw_area": req.raw_area,
        "area_sqm": area_sqm,
        "area_hectares": round(area_sqm / 10000.0, 4),
        "area_acres": round(area_sqm / 4046.856, 4),
        "detected_unit": detected_unit,
    }


@router.get("/units")
async def list_supported_units():
    """List supported vernacular units and conversion factors to m²."""
    return {"units": AREA_UNIT_CONVERSIONS_SQM}
