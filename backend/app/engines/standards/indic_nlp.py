"""
Indic & Vernacular Land Terminology NLP Mapper.

Maps regional revenue, survey, and cadastral terminology across Indian states
(Hindi/Devanagari, Marathi, Punjabi, Bengali, Telugu, Tamil, Kannada, etc.) into
BhuDrishti's canonical schema.

Features:
  1. Terminology translation dictionary & RapidFuzz phonetic normalization.
  2. Area unit conversion for Indian regional land measurement systems
     (Bigha, Biswa, Guntha, Kanal, Marla, Cent, Ground, Katha, Acre, Hectare) into SI m² and hectares.
  3. Raw properties dict standardization.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from rapidfuzz import fuzz, process

# Regional land measurement conversion factors to square meters (m²)
# Source: Department of Land Resources (DoLR), MoRD, Govt of India Land Unit Standards
AREA_UNIT_CONVERSIONS_SQM = {
    # Standard Metric & International
    "sqm": 1.0,
    "sq_m": 1.0,
    "sq_meter": 1.0,
    "sq_meters": 1.0,
    "square_meter": 1.0,
    "वर्ग मीटर": 1.0,
    "मी²": 1.0,
    "hectare": 10000.0,
    "ha": 10000.0,
    "हेक्टेयर": 10000.0,
    "acre": 4046.8564224,
    "ac": 4046.8564224,
    "एकड़": 4046.8564224,
    "sqft": 0.092903,
    "sq_ft": 0.092903,
    "square_feet": 0.092903,
    "वर्ग फुट": 0.092903,
    # North India / UP / Bihar / MP / Rajasthan / Punjab
    "bigha": 2529.289,  # Standard Pucca Bigha (3025 sq yards)
    "pucca_bigha": 2529.289,
    "kacha_bigha": 843.096,  # 1/3 of pucca bigha
    "बीघा": 2529.289,
    "पक्का बीघा": 2529.289,
    "कच्चा बीघा": 843.096,
    "biswa": 126.464,  # 1/20 of Bigha
    "बिस्वा": 126.464,
    "biswansi": 6.323,  # 1/20 of Biswa
    "बिस्वांसी": 6.323,
    "katha": 126.464,  # Bihar/Bengal Katha (~1361 sq ft)
    "कट्ठा": 126.464,
    "कट्टा": 126.464,
    "dhur": 6.323,
    "धूर": 6.323,
    # Punjab / Haryana / HP / J&K
    "kanal": 505.857,  # 1/8 acre (20 marlas)
    "कनाल": 505.857,
    "marla": 25.293,  # 1/20 kanal
    "मरला": 25.293,
    "sarsahi": 2.81,
    # Maharashtra / Gujarat / Karnataka / AP / Telangana
    "guntha": 101.171,  # 1/40 acre (1089 sq ft)
    "गुंठा": 101.171,
    "गुंटा": 101.171,
    "guntas": 101.171,
    "vigha": 1936.0,  # Gujarat Vigha
    "विघा": 1936.0,
    # South India (Tamil Nadu / Kerala / AP / Karnataka)
    "cent": 40.4686,  # 1/100 acre
    "सेंट": 40.4686,
    "ground": 222.967,  # 2400 sq ft (Tamil Nadu Urban)
    "ग्राउन्ड": 222.967,
    "ankanam": 6.689,  # AP
}

# Vernacular & Hindi revenue field mappings to Canonical Schema
INDIC_FIELD_MAP = {
    "parcel_id": [
        "khasra",
        "khasra_no",
        "khasra_number",
        "gata",
        "gata_no",
        "gata_sankhya",
        "plot_no",
        "survey_no",
        "survey_number",
        "chalta_no",
        "taram_no",
        "khatauni_khasra",
        "dag_no",
        "खसरा",
        "खसरा नं",
        "खसरा संख्या",
        "गाटा",
        "गाटा संख्या",
        "गट क्रमांक",
        "प्लॉट नं",
        "प्लॉट संख्या",
        "सर्वे नंबर",
        "दाघ नं",
        "చాల్తా నంబరు",
        "సర్వే నంబరు",
    ],
    "khata_number": [
        "khata",
        "khata_no",
        "khatauni",
        "khatauni_no",
        "khewat",
        "khewat_no",
        "jamabandi",
        "ror_id",
        "patta_no",
        "खाता",
        "खाता नं",
        "खाता संख्या",
        "खतौनी",
        "खतौनी नं",
        "खेवट",
        "खेवट नं",
        "जमाबंदी",
        "पट्टा संख्या",
        "ఖాతా నంబరు",
        "பட்டா எண்",
    ],
    "owner": [
        "malik",
        "owner_name",
        "kashthkar",
        "pattadar",
        "rayat",
        "bhoomi_swami",
        "khatedar",
        "tenure_holder",
        "occupant",
        "kabza",
        "dharak",
        "nam",
        "मालिक",
        "मालिक का नाम",
        "काश्तकार",
        "पट्टेदार",
        "खातेदार",
        "भूमि स्वामी",
        "खातेदाराचे नाव",
        "रैयत",
        "భూమి యజమాని",
        "பட்டாதாரர் பெயர்",
    ],
    "land_use": [
        "kism",
        "upayog",
        "prayojan",
        "land_type",
        "zoning",
        "classification",
        "usage",
        "vargikaran",
        "dharana_prakar",
        "किस्म",
        "किस्म ज़मीन",
        "उपयोग",
        "भूमि उपयोग",
        "प्रयोजन",
        "वर्गीकरण",
        "धोरण प्रकार",
        "நில வகைப்பாடு",
    ],
    "area": [
        "rakba",
        "kshetraphal",
        "pariman",
        "visteernam",
        "extent",
        "map",
        "area_raw",
        "रकबा",
        "क्षेत्रफल",
        "रकबा बीघा",
        "विस्तार",
        "విస్తీర్ణం",
        "பரப்பளவு",
    ],
    "village": [
        "mauza",
        "gram",
        "gaon",
        "mohalla",
        "village_name",
        "revenue_village",
        "deh",
        "मौजा",
        "ग्राम",
        "गांव",
        "गाँव",
        "मोहाल्ला",
        "గ్రామం",
        "கிராமம்",
    ],
    "tehsil": [
        "tehsil",
        "taluka",
        "mandal",
        "sub_district",
        "circle",
        "anchal",
        "तहसील",
        "तालुका",
        "मंडल",
        "अंचल",
        "తాలూకా",
        "வட்டம்",
    ],
    "district": [
        "jila",
        "district",
        "zila",
        "जिला",
        "जिल्हा",
        "జిల్లా",
        "மாவட்டம்",
    ],
}


def normalize_indic_key(key: str) -> str:
    """Normalize unicode and case for Hindi/Devanagari and Latin strings."""
    if not key:
        return ""
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", str(key)).strip().lower()
    text = re.sub(r"[_\-.\s/]+", " ", text)
    return text.strip()


def parse_indic_area(raw_value: Any, default_unit: str = "bigha") -> tuple[float | None, str]:
    """Parse raw Indic area string into normalized square meters (m²).

    Examples:
      "2 बीघा" -> (5058.58, "बीघा")
      "1 Bigha 5 Biswa" -> (3161.61, "bigha_biswa")
      "1200 sqm" -> (1200.0, "sqm")
      "4.5 Guntha" -> (455.27, "guntha")
    """
    if raw_value is None:
        return None, "unknown"
    if isinstance(raw_value, (int, float)):
        return float(raw_value), "numeric"

    val_str = str(raw_value).strip().lower()

    # Pattern: 1 Bigha 5 Biswa (compound area)
    compound_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:bigha|बीघा|vigha|विघा)\s*(?:and|,|\+)?\s*(\d+(?:\.\d+)?)\s*(?:biswa|बिस्वा|कट्टा|katha)", val_str)
    if compound_match:
        bighas = float(compound_match.group(1))
        biswas = float(compound_match.group(2))
        total_sqm = bighas * AREA_UNIT_CONVERSIONS_SQM["bigha"] + biswas * AREA_UNIT_CONVERSIONS_SQM["biswa"]
        return round(total_sqm, 2), "compound_bigha_biswa"

    # Single unit check
    for unit_name, factor in AREA_UNIT_CONVERSIONS_SQM.items():
        pattern = rf"(\d+(?:\.\d+)?)\s*{re.escape(unit_name)}"
        match = re.search(pattern, val_str)
        if match:
            num = float(match.group(1))
            return round(num * factor, 2), unit_name

    # Pure float extract fallback
    num_match = re.search(r"(\d+(?:\.\d+)?)", val_str)
    if num_match:
        val = float(num_match.group(1))
        # If number is small (< 50) and no unit given, likely bigha or acre
        return val, "raw_numeric"

    return None, "unparseable"


def map_indic_properties(
    properties: dict[str, Any],
    threshold: float = 75.0,
    state_context: str = "NATIONAL",
) -> dict[str, Any]:
    """Translates and maps a raw properties dictionary with Hindi/Vernacular
    keys to BhuDrishti canonical schema.

    Returns:
      {
        "parcel_id": "...",
        "owner": "...",
        "khata_number": "...",
        "land_use": "...",
        "village": "...",
        "area_sqm": float,
        "attributes": { ... other remaining/unmapped props ... }
      }
    """
    flat_synonyms: dict[str, str] = {}
    for canonical, syn_list in INDIC_FIELD_MAP.items():
        for syn in syn_list:
            flat_synonyms[normalize_indic_key(syn)] = canonical

    mapped: dict[str, Any] = {}
    unmapped: dict[str, Any] = {}
    area_sqm: float | None = None

    for raw_key, raw_val in properties.items():
        norm_key = normalize_indic_key(raw_key)

        # Direct match
        matched_canonical = flat_synonyms.get(norm_key)

        # Fuzzy match if no direct hit
        if not matched_canonical:
            match = process.extractOne(norm_key, flat_synonyms.keys(), scorer=fuzz.ratio)
            if match and match[1] >= threshold:
                matched_canonical = flat_synonyms[match[0]]

        if matched_canonical:
            if matched_canonical == "area":
                parsed_area, _ = parse_indic_area(raw_val)
                mapped["area"] = parsed_area
                area_sqm = parsed_area
            else:
                mapped[matched_canonical] = raw_val
        else:
            unmapped[raw_key] = raw_val

    return {
        "parcel_id": mapped.get("parcel_id"),
        "owner": mapped.get("owner"),
        "khata_number": mapped.get("khata_number"),
        "land_use": mapped.get("land_use"),
        "village": mapped.get("village"),
        "area_sqm": area_sqm,
        "attributes": {**mapped, **unmapped},
    }
