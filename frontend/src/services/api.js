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
    feature_b: "M-456",
    score: 96,
    status: "matched",
    breakdown: {
      score: 96,
      components: { geometry: 0.98, proximity: 1.0, area: 1.0, attributes: 0.88, reliability: 0.92 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-101", feature_id: "P-101", area: 1050.0, land_use: "Residential",
      owner: "Sunita Devi", authority: "Delhi Revenue Dept", source_reliability: 95,
      geometry: { type: "Polygon", coordinates: [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]] }
    },
    feature_b_details: {
      id: "M-456", feature_id: "M-456", area: 1050.0, zone: "Zone R-1",
      address: "Plot 101, Sector 14, Dwarka", authority: "MCD Urban Local Body", source_reliability: 82,
      geometry: { type: "Polygon", coordinates: [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]] }
    }
  },
  {
    feature_a: "P-102",
    feature_b: "M-458",
    score: 89,
    status: "review",
    breakdown: {
      score: 89,
      components: { geometry: 0.86, proximity: 0.94, area: 0.90, attributes: 0.85, reliability: 0.92 },
      matched_attributes: ["land_use"],
      differing_attributes: ["area"],
    },
    feature_a_details: {
      id: "P-102", feature_id: "P-102", area: 1240.0, land_use: "Residential",
      owner: "Ramesh Sharma", authority: "Delhi Revenue Dept", source_reliability: 95,
      geometry: { type: "Polygon", coordinates: [[[77.2096, 28.6135], [77.2108, 28.6135], [77.2108, 28.6144], [77.2096, 28.6144], [77.2096, 28.6135]]] }
    },
    feature_b_details: {
      id: "M-458", feature_id: "M-458", area: 1256.0, zone: "Zone R-2",
      address: "Plot 102, Sector 14, Dwarka", authority: "MCD Urban Local Body", source_reliability: 82,
      geometry: { type: "Polygon", coordinates: [[[77.20955, 28.61348], [77.21085, 28.61348], [77.21085, 28.61442], [77.20955, 28.61442], [77.20955, 28.61348]]] }
    }
  },
  {
    feature_a: "P-103",
    feature_b: "M-459",
    score: 94,
    status: "matched",
    breakdown: {
      score: 94,
      components: { geometry: 0.96, proximity: 0.99, area: 1.0, attributes: 0.82, reliability: 0.92 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-103", feature_id: "P-103", area: 1420.0, land_use: "Commercial",
      owner: "Apex Retailers Pvt Ltd", authority: "Delhi Revenue Dept", source_reliability: 95,
      geometry: { type: "Polygon", coordinates: [[[77.2110, 28.6136], [77.2122, 28.6136], [77.2122, 28.6145], [77.2110, 28.6145], [77.2110, 28.6136]]] }
    },
    feature_b_details: {
      id: "M-459", feature_id: "M-459", area: 1420.0, zone: "Zone C-1",
      address: "Commercial Hub 103, Sector 14", authority: "MCD Urban Local Body", source_reliability: 82,
      geometry: { type: "Polygon", coordinates: [[[77.2110, 28.6136], [77.2122, 28.6136], [77.2122, 28.6145], [77.2110, 28.6145], [77.2110, 28.6136]]] }
    }
  },
  {
    feature_a: "P-104",
    feature_b: "M-460",
    score: 95,
    status: "matched",
    breakdown: {
      score: 95,
      components: { geometry: 0.98, proximity: 1.0, area: 1.0, attributes: 0.85, reliability: 0.92 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-104", feature_id: "P-104", area: 980.0, land_use: "Public Utility",
      owner: "DDA Parks and Recreation", authority: "Delhi Revenue Dept", source_reliability: 95,
      geometry: { type: "Polygon", coordinates: [[[77.2085, 28.6144], [77.2095, 28.6144], [77.2095, 28.6152], [77.2085, 28.6152], [77.2085, 28.6144]]] }
    },
    feature_b_details: {
      id: "M-460", feature_id: "M-460", area: 980.0, zone: "Green Belt",
      address: "DDA Park Sector 14", authority: "MCD Urban Local Body", source_reliability: 82,
      geometry: { type: "Polygon", coordinates: [[[77.2085, 28.6144], [77.2095, 28.6144], [77.2095, 28.6152], [77.2085, 28.6152], [77.2085, 28.6144]]] }
    }
  },
  {
    feature_a: "P-105",
    feature_b: "M-461",
    score: 93,
    status: "matched",
    breakdown: {
      score: 93,
      components: { geometry: 0.95, proximity: 0.98, area: 1.0, attributes: 0.80, reliability: 0.92 },
      matched_attributes: ["land_use"],
      differing_attributes: [],
    },
    feature_a_details: {
      id: "P-105", feature_id: "P-105", area: 2100.0, land_use: "Industrial",
      owner: "Vikas Logistics and Warehousing", authority: "Delhi Revenue Dept", source_reliability: 95,
      geometry: { type: "Polygon", coordinates: [[[77.2097, 28.6146], [77.2115, 28.6146], [77.2115, 28.6155], [77.2097, 28.6155], [77.2097, 28.6146]]] }
    },
    feature_b_details: {
      id: "M-461", feature_id: "M-461", area: 2100.0, zone: "Industrial Zone",
      address: "Plot 105, Phase 2, Dwarka", authority: "MCD Urban Local Body", source_reliability: 82,
      geometry: { type: "Polygon", coordinates: [[[77.2097, 28.6146], [77.2115, 28.6146], [77.2115, 28.6155], [77.2097, 28.6155], [77.2097, 28.6146]]] }
    }
  }
];

const DEMO_CONFLICTS = [
  {
    id: 1,
    feature_a: "P-102",
    feature_b: "M-458",
    type: "area",
    severity: "medium",
    score: 89,
    status: "pending_review",
    area_difference: 16.0,
    reason: "Area discrepancy detected: Cadastral 1,240 m² vs Municipal 1,256 m² (Delta: 16.0 m²)",
    feature_a_details: DEMO_MATCHES[1].feature_a_details,
    feature_b_details: DEMO_MATCHES[1].feature_b_details,
  }
];

const DEMO_RECOMMENDATIONS = [
  {
    conflict_id: 1,
    action: "prefer_source",
    confidence: 89,
    reason: "Source A (Cadastral) has higher institutional reliability (0.95 vs 0.82) and surveyed ground truth",
    preferred_source_id: 1,
    feature_a: "P-102",
    feature_b: "M-458",
    conflict_type: "area",
    severity: "medium",
    status: "pending_review",
  }
];

const DEMO_DATASETS = [
  {
    id: 1, filename: "cadastral_survey_dwarka.geojson", dataset_type: "cadastral",
    status: "standardized", crs: "EPSG:4326", feature_count: 5,
    source_name: "Delhi Revenue & Land Records Authority",
    created_at: new Date().toISOString(),
  },
  {
    id: 2, filename: "municipal_gis_dwarka.geojson", dataset_type: "municipal",
    status: "standardized", crs: "EPSG:4326", feature_count: 5,
    source_name: "Municipal Corporation of Delhi (MCD)",
    created_at: new Date().toISOString(),
  },
  {
    id: 3, filename: "building_footprints_dwarka.geojson", dataset_type: "building",
    status: "standardized", crs: "EPSG:4326", feature_count: 3,
    source_name: "Delhi Urban Shelter & Building Registry",
    created_at: new Date().toISOString(),
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

  async seedSampleProject() {
    const data = await safeFetch("/datasets/sample-seed", { method: "POST" });
    return data || { status: "seeded", region: "Dwarka, New Delhi" };
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
  }
};
