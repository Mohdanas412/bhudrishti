"""
Tests for Standards Engine:
  1. ULPIN (Bhu-Aadhar) Geohash Generator & Validator (NAKSHA spec).
  2. Indic / Vernacular Land Records NLP Mapper and Area Unit Conversions.
  3. REST API Endpoints (/standards/ulpin/generate, /standards/indic-nlp/map, etc.).
"""

import pytest
from app.engines.standards.indic_nlp import (
    map_indic_properties,
    parse_indic_area,
)
from app.engines.standards.ulpin import (
    decode_ulpin,
    generate_ulpin,
    validate_ulpin,
)
from app.main import app
from fastapi.testclient import TestClient
from shapely.geometry import Polygon


@pytest.fixture
def client():
    return TestClient(app)


def test_ulpin_generation_and_validation():
    lat = 28.613939
    lon = 77.209021
    poly = Polygon([
        (77.2085, 28.6135),
        (77.2095, 28.6135),
        (77.2095, 28.6142),
        (77.2085, 28.6142),
        (77.2085, 28.6135),
    ])

    ulpin = generate_ulpin(lat, lon, polygon=poly)
    assert len(ulpin) == 14
    assert isinstance(ulpin, str)
    assert validate_ulpin(ulpin) is True

    # Check decoded values match original coordinates
    decoded = decode_ulpin(ulpin)
    assert abs(decoded["latitude"] - poly.centroid.y) < 0.001
    assert abs(decoded["longitude"] - poly.centroid.x) < 0.001
    assert decoded["valid"] is True


def test_ulpin_invalid():
    assert validate_ulpin("INVALID") is False
    assert validate_ulpin("12345678901234") is False  # wrong check digit


def test_indic_area_parsing():
    # 2 Bigha -> 5058.58 sqm
    sqm, unit = parse_indic_area("2 बीघा")
    assert sqm is not None
    assert abs(sqm - (2 * 2529.289)) < 1.0

    # Compound: 1 Bigha 5 Biswa -> 2529.289 + 5 * 126.464 = 3161.61 sqm
    sqm_comp, _ = parse_indic_area("1 Bigha 5 Biswa")
    assert sqm_comp is not None
    assert abs(sqm_comp - 3161.61) < 1.0

    # 4 Guntha -> 4 * 101.171 = 404.68 sqm
    sqm_g, _ = parse_indic_area("4 Guntha")
    assert sqm_g is not None
    assert abs(sqm_g - 404.68) < 1.0

    # 2 Kanal -> 2 * 505.857 = 1011.71 sqm
    sqm_k, _ = parse_indic_area("2 Kanal")
    assert sqm_k is not None
    assert abs(sqm_k - 1011.71) < 1.0


def test_indic_property_mapping():
    raw_props = {
        "खसरा": "102/4",
        "खाता": "KH-882",
        "मालिक": "रामेश शर्मा",
        "किस्म ज़मीन": "आवासीय (Residential)",
        "रकबा": "2 बीघा",
        "मौजा": "द्वारका",
    }

    result = map_indic_properties(raw_props)
    assert result["parcel_id"] == "102/4"
    assert result["khata_number"] == "KH-882"
    assert result["owner"] == "रामेश शर्मा"
    assert result["land_use"] == "आवासीय (Residential)"
    assert result["village"] == "द्वारका"
    assert result["area_sqm"] is not None
    assert abs(result["area_sqm"] - 5058.58) < 1.0


def test_standards_api_endpoints(client):
    # 1. Generate ULPIN
    gen_res = client.post("/standards/ulpin/generate", json={"latitude": 28.6139, "longitude": 77.2090})
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "ulpin" in gen_data
    assert len(gen_data["ulpin"]) == 14
    ulpin_code = gen_data["ulpin"]

    # 2. Validate ULPIN
    val_res = client.post("/standards/ulpin/validate", json={"ulpin": ulpin_code})
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True

    # 3. Decode ULPIN
    dec_res = client.post("/standards/ulpin/decode", json={"ulpin": ulpin_code})
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert abs(dec_data["latitude"] - 28.6139) < 0.01

    # 4. Indic NLP translation endpoint
    indic_res = client.post(
        "/standards/indic-nlp/map",
        json={"properties": {"खसरा": "P-909", "मालिक": "सुनीता देवी", "रकबा": "1.5 बीघा"}},
    )
    assert indic_res.status_code == 200
    canonical = indic_res.json()["canonical"]
    assert canonical["parcel_id"] == "P-909"
    assert canonical["owner"] == "सुनीता देवी"

    # 5. Convert Area endpoint
    area_res = client.post("/standards/indic-nlp/convert-area", json={"raw_area": "4 Guntha"})
    assert area_res.status_code == 200
    assert area_res.json()["area_sqm"] > 400.0
