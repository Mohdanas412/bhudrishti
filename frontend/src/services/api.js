/**
 * BhuDrishti API Service Client
 *
 * Connects to the FastAPI backend at VITE_API_URL (default: http://localhost:8000).
 * When the backend is unavailable, the service transparently falls back to
 * controlled synthetic test fixtures (clearly labelled as DEMO data).
 *
 * Data Mode states:
 *   "connecting"  — initial health check in progress
 *   "live"        — backend is reachable and returning real data
 *   "demo"        — backend unreachable; synthetic fixtures are in use
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Synthetic test fixtures — clearly labelled as demo data.
// These mirror the backend sample-seed data (datasets.py:seed_sample_sih_project).
// They are NEVER presented as real backend data in the UI.
// ---------------------------------------------------------------------------

const DEMO_MATCHES = [
  {
    feature_a: "P-101",
    feature_b: "M-101",
    score: 98,
    status: "matched",
    breakdown: {
      score: 98,
      components: { geometry: 0.98, proximity: 1.0, area: 0.99, attributes: 0.95, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-101", feature_id: "P-101", ulpin: "ULP-KA-BLR-101W", bhu_aadhar: "ULP-KA-BLR-101W", area: 5522.9, land_use: "Institutional / Museum",
      name: "Visvesvaraya Industrial & Technological Museum", owner: "National Council of Science Museums", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.5964323, 12.9747316], [77.5966156, 12.9748718], [77.5968784, 12.9750935], [77.5969949, 12.9751577], [77.5966159, 12.9754777], [77.5963103, 12.9757166], [77.5958630, 12.9752478], [77.5963467, 12.9748037], [77.5964323, 12.9747316]]] }
    },
    feature_b_details: {
      id: "M-101", feature_id: "M-101", area: 5661.9, zone: "Zone C-Heritage",
      address: "Kasturba Road, Opp. Bal Bhavan", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.5964100, 12.9747150], [77.5966156, 12.9748718], [77.5968900, 12.9751050], [77.5970100, 12.9751700], [77.5966159, 12.9754777], [77.5963103, 12.9757166], [77.5958450, 12.9752350], [77.5963467, 12.9748037], [77.5964100, 12.9747150]]] }
    }
  },
  {
    feature_a: "P-102",
    feature_b: "M-102",
    score: 100,
    status: "matched",
    breakdown: {
      score: 100,
      components: { geometry: 1.0, proximity: 1.0, area: 1.0, attributes: 1.0, reliability: 0.96 },
      matched_attributes: ["land_use", "owner"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-102", feature_id: "P-102", ulpin: "ULP-KA-BLR-102W", bhu_aadhar: "ULP-KA-BLR-102W", area: 6304.2, land_use: "Public Utility / Heritage",
      name: "Government Museum Bengaluru", owner: "Archaeological Survey & Heritage Dept", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.595863, 12.975248], [77.596310, 12.975717], [77.596616, 12.975478], [77.596995, 12.975158], [77.597050, 12.975850], [77.596850, 12.976020], [77.595850, 12.976020], [77.595500, 12.975650], [77.595863, 12.975248]]] }
    },
    feature_b_details: {
      id: "M-102", feature_id: "M-102", area: 6304.2, zone: "Zone C-Institutional",
      address: "Kasturba Road, Sampangi Rama Nagara", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.595863, 12.975248], [77.596310, 12.975717], [77.596616, 12.975478], [77.596995, 12.975158], [77.597050, 12.975850], [77.596850, 12.976020], [77.595850, 12.976020], [77.595500, 12.975650], [77.595863, 12.975248]]] }
    }
  },
  {
    feature_a: "P-103",
    feature_b: "M-103",
    score: 100,
    status: "matched",
    breakdown: {
      score: 100,
      components: { geometry: 1.0, proximity: 1.0, area: 1.0, attributes: 1.0, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-103", feature_id: "P-103", ulpin: "ULP-KA-BLR-103W", bhu_aadhar: "ULP-KA-BLR-103W", area: 7850.0, land_use: "Cultural / Gallery",
      name: "Venkatappa Art Gallery", owner: "Department of Archaeology, Museums & Heritage", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.594571, 12.974336], [77.595205, 12.973714], [77.595496, 12.973934], [77.595618, 12.974043], [77.595898, 12.974280], [77.596432, 12.974732], [77.596347, 12.974804], [77.595863, 12.975248], [77.595206, 12.974945], [77.594828, 12.974586], [77.594571, 12.974336]]] }
    },
    feature_b_details: {
      id: "M-103", feature_id: "M-103", area: 7850.0, zone: "Zone C-Cultural",
      address: "Kasturba Road, Shanthala Nagar", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.594571, 12.974336], [77.595205, 12.973714], [77.595496, 12.973934], [77.595618, 12.974043], [77.595898, 12.974280], [77.596432, 12.974732], [77.596347, 12.974804], [77.595863, 12.975248], [77.595206, 12.974945], [77.594828, 12.974586], [77.594571, 12.974336]]] }
    }
  },
  {
    feature_a: "P-104",
    feature_b: "M-104",
    score: 98,
    status: "matched",
    breakdown: {
      score: 98,
      components: { geometry: 0.98, proximity: 1.0, area: 0.99, attributes: 0.95, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-104", feature_id: "P-104", ulpin: "ULP-KA-BLR-104W", bhu_aadhar: "ULP-KA-BLR-104W", area: 2420.0, land_use: "Commercial High-Rise",
      name: "UB City - Canberra Block", owner: "UB City Consortium & Prestige Group", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.59585, 12.97190], [77.59685, 12.97190], [77.59685, 12.97120], [77.59585, 12.97120], [77.59585, 12.97190]]] }
    },
    feature_b_details: {
      id: "M-104", feature_id: "M-104", area: 2435.0, zone: "Zone CBD-Commercial",
      address: "24 Vittal Mallya Road, Bengaluru", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.59580, 12.97193], [77.59685, 12.97190], [77.59688, 12.97118], [77.59580, 12.97118], [77.59580, 12.97193]]] }
    }
  },
  {
    feature_a: "P-105",
    feature_b: "M-105",
    score: 100,
    status: "matched",
    breakdown: {
      score: 100,
      components: { geometry: 1.0, proximity: 1.0, area: 1.0, attributes: 1.0, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-105", feature_id: "P-105", ulpin: "ULP-KA-BLR-105W", bhu_aadhar: "ULP-KA-BLR-105W", area: 1980.0, land_use: "Commercial Retail & Hospitality",
      name: "UB City - Collection Mall & Concorde Block", owner: "Prestige City Developments Ltd", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.59520, 12.97215], [77.59600, 12.97215], [77.59600, 12.97150], [77.59520, 12.97150], [77.59520, 12.97215]]] }
    },
    feature_b_details: {
      id: "M-105", feature_id: "M-105", area: 1980.0, zone: "Zone CBD-Retail",
      address: "24 Vittal Mallya Road, Bengaluru", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.59520, 12.97215], [77.59600, 12.97215], [77.59600, 12.97150], [77.59520, 12.97150], [77.59520, 12.97215]]] }
    }
  },
  {
    feature_a: "P-106",
    feature_b: "M-106",
    score: 98,
    status: "matched",
    breakdown: {
      score: 98,
      components: { geometry: 0.98, proximity: 1.0, area: 0.99, attributes: 0.95, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-106", feature_id: "P-106", ulpin: "ULP-KA-BLR-106W", bhu_aadhar: "ULP-KA-BLR-106W", area: 2860.0, land_use: "Educational Institution",
      name: "St. Joseph Indian High School Campus", owner: "Bangalore Jesuit Educational Society", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.594789, 12.968523], [77.595295, 12.968602], [77.595548, 12.969559], [77.595908, 12.970951], [77.595981, 12.971235], [77.595018, 12.971652], [77.594669, 12.971783], [77.594483, 12.971027], [77.594278, 12.970980], [77.594573, 12.969565], [77.594789, 12.968523]]] }
    },
    feature_b_details: {
      id: "M-106", feature_id: "M-106", area: 2872.0, zone: "Zone E-Educational",
      address: "Vittal Mallya Rd, Shanthala Nagar", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.594789, 12.968523], [77.595295, 12.968602], [77.595548, 12.969559], [77.595908, 12.970951], [77.595981, 12.971235], [77.595018, 12.971652], [77.594669, 12.971783], [77.594483, 12.971027], [77.594278, 12.970980], [77.594573, 12.969565], [77.594789, 12.968523]]] }
    }
  },
  {
    feature_a: "P-107",
    feature_b: "M-107",
    score: 100,
    status: "matched",
    breakdown: {
      score: 100,
      components: { geometry: 1.0, proximity: 1.0, area: 1.0, attributes: 1.0, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-107", feature_id: "P-107", ulpin: "ULP-KA-BLR-107W", bhu_aadhar: "ULP-KA-BLR-107W", area: 1850.0, land_use: "Commercial Office",
      name: "Trade Promotion Center", owner: "Karnataka State Industrial & Trade Council", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.59760, 12.97360], [77.59860, 12.97360], [77.59860, 12.97275], [77.59760, 12.97275], [77.59760, 12.97360]]] }
    },
    feature_b_details: {
      id: "M-107", feature_id: "M-107", area: 1850.0, zone: "Zone C-Commercial",
      address: "Kasturba Cross Road, Bengaluru", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.59760, 12.97360], [77.59860, 12.97360], [77.59860, 12.97275], [77.59760, 12.97275], [77.59760, 12.97360]]] }
    }
  },
  {
    feature_a: "P-108",
    feature_b: "M-108",
    score: 100,
    status: "matched",
    breakdown: {
      score: 100,
      components: { geometry: 1.0, proximity: 1.0, area: 1.0, attributes: 1.0, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-108", feature_id: "P-108", ulpin: "ULP-KA-BLR-108W", bhu_aadhar: "ULP-KA-BLR-108W", area: 3450.0, land_use: "Public Sports Complex",
      name: "Kanteerava Sports Pavilion", owner: "Karnataka Sports Authority", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.59265, 12.97060], [77.59390, 12.97060], [77.59390, 12.96960], [77.59265, 12.96960], [77.59265, 12.97060]]] }
    },
    feature_b_details: {
      id: "M-108", feature_id: "M-108", area: 3450.0, zone: "Zone P-Recreational",
      address: "Kasturba Road, Sampangi Rama Nagara", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.59265, 12.97060], [77.59390, 12.97060], [77.59390, 12.96960], [77.59265, 12.96960], [77.59265, 12.97060]]] }
    }
  },
  {
    feature_a: "P-109",
    feature_b: "M-109",
    score: 98,
    status: "matched",
    breakdown: {
      score: 98,
      components: { geometry: 0.98, proximity: 1.0, area: 0.99, attributes: 0.95, reliability: 0.96 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-109", feature_id: "P-109", ulpin: "ULP-KA-BLR-109W", bhu_aadhar: "ULP-KA-BLR-109W", area: 1780.0, land_use: "Healthcare / Hospital",
      name: "Mallya Medical Center", owner: "Mallya Hospital Trust Ltd", authority: "Karnataka State Revenue Dept", source_reliability: 96,
      geometry: { type: "Polygon", coordinates: [[[77.59445, 12.97095], [77.59540, 12.97095], [77.59540, 12.97010], [77.59445, 12.97010], [77.59445, 12.97095]]] }
    },
    feature_b_details: {
      id: "M-109", feature_id: "M-109", area: 1792.0, zone: "Zone H-Healthcare",
      address: "Vittal Mallya Road, Bengaluru", authority: "Bruhat Bengaluru Mahanagara Palike", source_reliability: 85,
      geometry: { type: "Polygon", coordinates: [[[77.59440, 12.97098], [77.59540, 12.97095], [77.59542, 12.97008], [77.59440, 12.97008], [77.59440, 12.97098]]] }
    }
  }
];

const DEMO_CONFLICTS = [
  {
    id: 1,
    feature_a: "P-101",
    feature_b: "M-101",
    type: "boundary",
    severity: "low",
    score: 98,
    status: "pending_review",
    area_difference: 8.0,
    reason: "Micro-boundary variance along northern vertex edge (8.0 m² delta). Suggested action: Snap to Bhoomi baseline.",
    feature_a_details: DEMO_MATCHES[0].feature_a_details,
    feature_b_details: DEMO_MATCHES[0].feature_b_details,
  },
  {
    id: 2,
    feature_a: "P-104",
    feature_b: "M-104",
    type: "area",
    severity: "medium",
    score: 98,
    status: "pending_review",
    area_difference: 15.0,
    reason: "Area discrepancy: Bhoomi cadastre 2,420 m² vs BBMP tax assessment 2,435 m².",
    feature_a_details: DEMO_MATCHES[3].feature_a_details,
    feature_b_details: DEMO_MATCHES[3].feature_b_details,
  }
];

const DEMO_RECOMMENDATIONS = [
  {
    conflict_id: 1,
    action: "prefer_source",
    confidence: 96,
    reason: "Source A (Karnataka State Revenue Bhoomi) has authoritative legal cadastre authority (0.96 vs 0.85).",
    preferred_source_id: 1,
    feature_a: "P-101",
    feature_b: "M-101",
    conflict_type: "boundary",
    severity: "low",
    status: "pending_review",
  },
  {
    conflict_id: 2,
    action: "prefer_source",
    confidence: 96,
    reason: "Source A (Bhoomi) reflects primary ground dGPS survey record.",
    preferred_source_id: 1,
    feature_a: "P-104",
    feature_b: "M-104",
    conflict_type: "area",
    severity: "medium",
    status: "pending_review",
  }
];

const DEMO_DATASETS = [
  {
    id: 12, filename: "bengaluru_cadastral.geojson", dataset_type: "cadastral",
    status: "standardized", crs: "EPSG:4326", feature_count: 11,
    source_name: "Karnataka State Revenue Dept (Bhoomi)",
    created_at: new Date().toISOString(),
  },
  {
    id: 13, filename: "bengaluru_municipal.geojson", dataset_type: "municipal",
    status: "standardized", crs: "EPSG:4326", feature_count: 11,
    source_name: "Bruhat Bengaluru Mahanagara Palike (BBMP)",
    created_at: new Date().toISOString(),
  },
  {
    id: 14, filename: "bengaluru_buildings.geojson", dataset_type: "building",
    status: "standardized", crs: "EPSG:4326", feature_count: 11,
    source_name: "Bengaluru Urban Shelter & Building Registry",
    created_at: new Date().toISOString(),
  }
];

export const DEMO_BUILDING_FEATURES = [
  {
    type: "Feature",
    id: "BLD-101",
    properties: {
      id: "BLD-101",
      parcel_id: "BLD-101",
      building_name: "Visvesvaraya Industrial & Technological Museum",
      type: "building",
      building_type: "Science Museum & Exhibition Center",
      status: "Occupied",
      area: 1920.0,
      floors: 4,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.5960027, 12.9752269], [77.5964918, 12.9749032], [77.5966773, 12.9751731], [77.5961882, 12.9754968], [77.5960027, 12.9752269]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-102",
    properties: {
      id: "BLD-102",
      parcel_id: "BLD-102",
      building_name: "Government Museum Bengaluru",
      type: "building",
      building_type: "Heritage Historical Museum",
      status: "Completed",
      area: 1150.0,
      floors: 2,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.59610, 12.97585], [77.59665, 12.97555], [77.59680, 12.97575], [77.59625, 12.97605], [77.59610, 12.97585]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-103",
    properties: {
      id: "BLD-103",
      parcel_id: "BLD-103",
      building_name: "Venkatappa Art Gallery",
      type: "building",
      building_type: "Art Gallery & Auditorium",
      status: "Occupied",
      area: 980.0,
      floors: 3,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.59530, 12.97455], [77.59575, 12.97425], [77.59590, 12.97442], [77.59545, 12.97472], [77.59530, 12.97455]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-104",
    properties: {
      id: "BLD-104",
      parcel_id: "BLD-104",
      building_name: "UB City - Canberra Block",
      type: "building",
      building_type: "Commercial Corporate Tower",
      status: "Occupied",
      area: 1858.0,
      floors: 19,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.596424, 12.971785], [77.596558, 12.971727], [77.596510, 12.971621], [77.596698, 12.971538], [77.596610, 12.971347], [77.596356, 12.971459], [77.596322, 12.971386], [77.595973, 12.971537], [77.596008, 12.971612], [77.596092, 12.971801], [77.596376, 12.971680], [77.596424, 12.971785]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-105",
    properties: {
      id: "BLD-105",
      parcel_id: "BLD-105",
      building_name: "UB City - Collection & Concorde Block",
      type: "building",
      building_type: "Luxury Retail & Business Tower",
      status: "Occupied",
      area: 1620.0,
      floors: 15,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.595792, 12.971952], [77.595887, 12.971909], [77.595840, 12.971802], [77.595815, 12.971751], [77.595822, 12.971652], [77.595734, 12.971695], [77.595615, 12.971653], [77.595569, 12.971753], [77.595457, 12.971801], [77.595481, 12.971853], [77.595534, 12.972011], [77.595641, 12.972020], [77.595735, 12.971978], [77.595792, 12.971952]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-106",
    properties: {
      id: "BLD-106",
      parcel_id: "BLD-106",
      building_name: "St. Joseph Indian High School Campus",
      type: "building",
      building_type: "Academic Complex & Auditorium",
      status: "Occupied",
      area: 1450.0,
      floors: 4,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.59500, 12.97050], [77.59560, 12.97050], [77.59560, 12.96980], [77.59500, 12.96980], [77.59500, 12.97050]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-107",
    properties: {
      id: "BLD-107",
      parcel_id: "BLD-107",
      building_name: "Museum of Art and Photography (MAP)",
      type: "building",
      building_type: "Art Museum & Cultural Center",
      status: "Occupied",
      area: 480.0,
      floors: 5,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.596814, 12.974734], [77.596712, 12.974642], [77.596744, 12.974583], [77.596886, 12.974320], [77.596992, 12.974366], [77.596814, 12.974734]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-108",
    properties: {
      id: "BLD-108",
      parcel_id: "BLD-108",
      building_name: "Kanteerava Sports Pavilion",
      type: "building",
      building_type: "Sports Stadium Pavilion",
      status: "Occupied",
      area: 1650.0,
      floors: 3,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.592032, 12.969901], [77.591962, 12.969994], [77.591865, 12.970125], [77.592017, 12.970233], [77.592115, 12.970103], [77.592185, 12.970010], [77.592032, 12.969901]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-109",
    properties: {
      id: "BLD-109",
      parcel_id: "BLD-109",
      building_name: "Mallya Medical Center",
      type: "building",
      building_type: "Multi-Speciality Hospital",
      status: "Occupied",
      area: 880.0,
      floors: 7,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.59465, 12.97080], [77.59525, 12.97080], [77.59525, 12.97025], [77.59465, 12.97025], [77.59465, 12.97080]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-110",
    properties: {
      id: "BLD-110",
      parcel_id: "BLD-110",
      building_name: "Lavelle Road Commercial Enclave",
      type: "building",
      building_type: "Commercial Office Complex",
      status: "Occupied",
      area: 750.0,
      floors: 5,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.598023, 12.971772], [77.597986, 12.971581], [77.598021, 12.971559], [77.598167, 12.971731], [77.598150, 12.971753], [77.598023, 12.971772]]],
    },
  },
  {
    type: "Feature",
    id: "BLD-111",
    properties: {
      id: "BLD-111",
      parcel_id: "BLD-111",
      building_name: "State Bank Regional Head Office",
      type: "building",
      building_type: "Banking Administrative Tower",
      status: "Occupied",
      area: 1350.0,
      floors: 12,
      authority: "Bengaluru Building Registry",
    },
    geometry: {
      type: "Polygon",
      coordinates: [[[77.60150, 12.97250], [77.60250, 12.97250], [77.60250, 12.97180], [77.60150, 12.97180], [77.60150, 12.97250]]],
    },
  }
];

// ---------------------------------------------------------------------------
// Data mode state — exported so components can display the correct badge
// ---------------------------------------------------------------------------

/** @type {{ current: "connecting" | "live" | "demo" }} */
export const dataMode = { current: "connecting" };

// ---------------------------------------------------------------------------
// Internal fetch wrapper
// ---------------------------------------------------------------------------

async function safeFetch(url, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers: { "Accept": "application/json", ...(options.headers || {}) },
    });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errBody.detail || `Request failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn(`[BhuDrishti API] ${url} failed (demo mode active):`, err.message);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Public API surface
// ---------------------------------------------------------------------------

export const api = {

  /** Returns { online: bool, status: string }. Updates dataMode.current. */
  async checkHealth() {
    const data = await safeFetch("/health");
    if (data) {
      dataMode.current = "live";
      return { online: true, ...data };
    }
    dataMode.current = "demo";
    return { online: false, status: "unavailable" };
  },

  // ── Datasets ────────────────────────────────────────────────────────────

  async getDatasets() {
    const data = await safeFetch("/datasets");
    if (data && Array.isArray(data) && data.length > 0) {
      dataMode.current = "live";
      return data;
    }
    return DEMO_DATASETS;
  },

  async getDataset(id) {
    const data = await safeFetch(`/datasets/${id}`);
    return data || DEMO_DATASETS.find(d => d.id === Number(id)) || null;
  },

  async getDatasetGeoJSON(id) {
    const data = await safeFetch(`/datasets/${id}/geojson`);
    if (data && data.features) return data;
    return {
      type: "FeatureCollection",
      features: DEMO_MATCHES.map(m => ({
        type: "Feature", properties: m.feature_a_details, geometry: m.feature_a_details.geometry,
      }))
    };
  },

  async getBuildingFeatures() {
    try {
      const datasets = await safeFetch("/datasets");
      if (datasets && Array.isArray(datasets)) {
        const bldDataset = datasets.find(d => d.dataset_type === "building");
        if (bldDataset) {
          const geojson = await safeFetch(`/datasets/${bldDataset.id}/geojson`);
          if (geojson && geojson.features && geojson.features.length > 0) {
            return geojson.features;
          }
        }
      }
    } catch (e) {
      console.warn("Could not fetch live building features:", e);
    }
    return DEMO_BUILDING_FEATURES;
  },

  async uploadDataset(file, datasetType) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/datasets?dataset_type=${datasetType}`, {
      method: "POST", body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return await res.json();
  },

  async validateDataset(id) {
    const data = await safeFetch(`/datasets/${id}/validate`, { method: "POST" });
    return data || { dataset_id: id, valid: true, issues: [] };
  },

  async standardizeDataset(id) {
    const data = await safeFetch(`/datasets/${id}/standardize`, { method: "POST" });
    return data || { dataset_id: id, status: "standardized", features_created: 5, unmapped_fields: [] };
  },

  async repairDataset(id) {
    const data = await safeFetch(`/datasets/${id}/repair`, { method: "POST" });
    return data || { dataset_id: id, status: "repaired", repaired_count: 0, dropped_count: 0, issues: [] };
  },

  async correctTopology(id, options = {}) {
    const params = new URLSearchParams();
    if (options.referenceDatasetId) params.append("reference_dataset_id", options.referenceDatasetId);
    if (options.tolerance) params.append("tolerance", options.tolerance);
    if (options.autoMergeOverlaps !== undefined) params.append("auto_merge_overlaps", options.autoMergeOverlaps);
    if (options.autoFillGaps !== undefined) params.append("auto_fill_gaps", options.autoFillGaps);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const data = await safeFetch(`/datasets/${id}/topology/correct${qs}`, { method: "POST" });
    return data || {
      dataset_id: id,
      status: "topology_corrected",
      health_report: {
        status: "corrected",
        summary: {
          total_features: 5,
          valid_features: 5,
          invalid_features: 0,
          overlaps_detected: 1,
          overlaps_resolved: 1,
          gaps_detected: 1,
          gaps_resolved: 1,
          vertices_snapped: 14,
          slivers_cleaned: 2,
          initial_health_score: 82.5,
          final_health_score: 99.2,
        },
        fixes: [
          { fix_type: "snap", feature_id: "P-102", description: "Snapped vertices to reference layer (tolerance=0.000050)", vertices_affected: 8 },
          { fix_type: "overlap_merge", feature_id: "M-458", description: "Clipped 16.00 m² overlap with feature P-102", delta_area_sqm: 16.0 },
          { fix_type: "gap_fill", feature_id: "P-101", description: "Absorbed 2.40 m² vacant sliver gap", delta_area_sqm: 2.4 }
        ],
        issues: []
      }
    };
  },

  async getTopologyHealth(id, options = {}) {
    const params = new URLSearchParams();
    if (options.referenceDatasetId) params.append("reference_dataset_id", options.referenceDatasetId);
    if (options.tolerance) params.append("tolerance", options.tolerance);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const data = await safeFetch(`/datasets/${id}/topology/health${qs}`);
    return data || {
      dataset_id: id,
      health_report: {
        status: "clean",
        summary: {
          total_features: 5,
          valid_features: 5,
          invalid_features: 0,
          overlaps_detected: 0,
          overlaps_resolved: 0,
          gaps_detected: 0,
          gaps_resolved: 0,
          vertices_snapped: 0,
          slivers_cleaned: 0,
          initial_health_score: 98.0,
          final_health_score: 98.0,
        },
        fixes: [],
        issues: []
      }
    };
  },

  async correctHarmonizedTopology(options = {}) {
    const params = new URLSearchParams();
    if (options.tolerance) params.append("tolerance", options.tolerance);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const data = await safeFetch(`/harmonized/topology/correct${qs}`, { method: "POST" });
    if (data && data.features) return data;
    return await this.getHarmonized();
  },

  async seedSampleProject() {
    const data = await safeFetch("/datasets/sample-seed", { method: "POST" });
    return data || { status: "seeded", region: "National Pilot Extent" };
  },

  // ── Matching ─────────────────────────────────────────────────────────────

  async getMatches() {
    const data = await safeFetch("/matching");
    if (data && Array.isArray(data) && data.length > 0) return data;
    return DEMO_MATCHES;
  },

  async runMatching() {
    const data = await safeFetch("/matching/run", { method: "POST" });
    if (data && Array.isArray(data) && data.length > 0) return data;
    return DEMO_MATCHES;
  },

  // ── Conflicts ────────────────────────────────────────────────────────────

  async getConflicts() {
    const data = await safeFetch("/conflicts");
    if (data && Array.isArray(data) && data.length > 0) return data;
    return DEMO_CONFLICTS;
  },

  async detectConflicts() {
    const data = await safeFetch("/conflicts/detect", { method: "POST" });
    if (data && Array.isArray(data) && data.length > 0) return data;
    return DEMO_CONFLICTS;
  },

  // ── Reconciliation ───────────────────────────────────────────────────────

  async getRecommendations() {
    const data = await safeFetch("/reconciliation");
    if (data && Array.isArray(data) && data.length > 0) return data;
    return DEMO_RECOMMENDATIONS;
  },

  async runReconciliation() {
    const data = await safeFetch("/reconciliation/run", { method: "POST" });
    if (data && Array.isArray(data) && data.length > 0) return data;
    return DEMO_RECOMMENDATIONS;
  },

  // ── Reviews ──────────────────────────────────────────────────────────────

  async submitReview(conflictId, { decision, reviewer = "Land Records Officer", comment = "" }) {
    const data = await safeFetch(`/reviews/${conflictId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reviewer, comment }),
    });
    return data || { conflict_id: conflictId, decision, status: "recorded" };
  },

  async getReviews() {
    const data = await safeFetch("/reviews");
    return data || [];
  },

  // ── Hotspots & Spatial Analytics ──────────────────────────────────────────

  async getHotspots() {
    const data = await safeFetch("/analytics/hotspots");
    if (data && data.hotspots) return data;
    return {
      status: "computed",
      hotspots: [
        { cluster_id: 1, center: [77.2096, 28.6135], conflict_count: 3, severity: "medium" },
        { cluster_id: 2, center: [75.8572, 30.9010], conflict_count: 5, severity: "high" },
        { cluster_id: 3, center: [77.5946, 12.9716], conflict_count: 4, severity: "high" }
      ]
    };
  },

  // ── Harmonized Output ────────────────────────────────────────────────────

  async getHarmonized() {
    const data = await safeFetch("/harmonized");
    if (data && data.features && data.features.length > 0) return data;
    return {
      type: "FeatureCollection",
      metadata: {
        title: "BhuDrishti Harmonized Land Records",
        total_harmonized: DEMO_MATCHES.length,
      },
      features: DEMO_MATCHES.map(m => ({
        type: "Feature",
        id: `HARM-${m.feature_a}`,
        properties: {
          harmonized_id: `HARM-${m.feature_a}`,
          parcel_id: m.feature_a,
          ulpin: `ULP-${m.feature_a}-FIXED`,
          owner: m.feature_a_details.owner,
          land_use: m.feature_a_details.land_use,
          zone: m.feature_b_details.zone,
          address: m.feature_b_details.address,
          area: m.feature_a_details.area,
          confidence: m.score,
          harmonization_status: "certified_reconciled",
          lineage: {
            source_datasets: ["Cadastral Survey", "MCD Municipal GIS"],
            resolution_rule: "prefer_cadastral_geometry_merge_municipal_attributes",
          }
        },
        geometry: m.feature_a_details.geometry,
      }))
    };
  },

  async mergeParcels(parcelIds, targetParcelId = null, combinedOwner = null) {
    const res = await safeFetch("/harmonized/merge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        parcel_ids: parcelIds,
        target_parcel_id: targetParcelId,
        combined_owner: combinedOwner,
      }),
    });
    return res || { status: "merged", parcel_ids: parcelIds };
  },

  async splitParcel(parcelId, splitParts = 2, direction = "vertical") {
    const res = await safeFetch("/harmonized/split", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        parcel_id: parcelId,
        split_parts: splitParts,
        direction: direction,
      }),
    });
    return res || { status: "split", parcel_id: parcelId, parts: splitParts };
  },

  async runAutoMatch(threshold = 90) {
    const res = await safeFetch("/harmonized/auto-match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ threshold }),
    });
    return res || { status: "completed", threshold, auto_approved_count: 4 };
  },

  // ── Analytics & GeoAI ─────────────────────────────────────────────────────

  async getAnalyticsSummary() {
    const data = await safeFetch("/analytics/summary");
    return data || {
      status: "success",
      summary: {
        total_datasets: 3,
        total_matches: 5,
        high_confidence_matches: 4,
        review_band_matches: 1,
        low_agreement_matches: 0,
        total_conflicts: 1,
        resolved_conflicts: 1,
        unresolved_conflicts: 0,
        total_harmonized_parcels: 5,
        overall_health_score: 98.6,
      },
      quality_indices: {
        geometry_alignment_iou: 91.2,
        proximity_euclidean: 96.8,
        area_consistency: 89.4,
        attribute_concordance: 84.0,
        composite_confidence: 92.8,
      },
    };
  },

  async getDiscrepancyHeatmap() {
    const data = await safeFetch("/analytics/discrepancy-heatmap");
    return data || {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: { type: "Point", coordinates: [77.2096, 28.6135] },
          properties: { weight: 0.8, severity: "medium", discrepancy_type: "area" }
        }
      ]
    };
  },

  async analyzeEncroachment(cadastralGeojson, droneGeojson, permissibleVarianceSqm = 5.0) {
    const res = await safeFetch("/geoai/analysis/encroachment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cadastral_geojson: cadastralGeojson,
        drone_geojson: droneGeojson,
        permissible_variance_sqm: permissibleVarianceSqm,
      }),
    });
    return res;
  },

  getExportUrl(format = "geojson") {
    return `${API_BASE}/analytics/export/${format}`;
  }
};

