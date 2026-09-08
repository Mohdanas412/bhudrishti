import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api } from "../services/api";
import {
  IconCrosshair,
  IconMaximize,
  IconChevronUp,
  IconChevronDown,
  IconCheck,
  IconAlertCircle,
  IconShield,
  IconSearch,
  IconFilter
} from "../components/Icons";

const BASEMAPS = {
  vector: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
  satellite: {
    version: 8,
    sources: {
      "esri-satellite": {
        type: "raster",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
        tileSize: 256,
        attribution: "Esri, Maxar, Earthstar Geographics"
      }
    },
    layers: [
      {
        id: "esri-satellite-layer",
        type: "raster",
        source: "esri-satellite",
        minzoom: 0,
        maxzoom: 19
      }
    ]
  }
};

export default function HarmonizationWorkspace() {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const location = useLocation();

  const [matches, setMatches] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [basemapMode, setBasemapMode] = useState("vector");
  const [queueOpen, setQueueOpen] = useState(false); // Collapsed by default per Section 27
  const [evidenceExpanded, setEvidenceExpanded] = useState(true);
  const [editDecisionModal, setEditDecisionModal] = useState(false);
  const [customComment, setCustomComment] = useState("");

  const [layersVisibility, setLayersVisibility] = useState({
    cadastral: true,
    municipal: true,
    building: true,
  });

  const [reviewMessage, setReviewMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mapReady, setMapReady] = useState(false);
  const hasFittedRef = useRef(false);
  // Set when the user lands here via "Investigate" from the Match Review page,
  // so the map zooms to that specific feature instead of the whole extent.
  const pendingFocusRef = useRef(null);

  // Load initial matching, conflict & recommendation data
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const [matchesData, conflictsData, recsData] = await Promise.all([
        api.getMatches(),
        api.getConflicts(),
        api.getRecommendations(),
      ]);
      setMatches(matchesData);
      setConflicts(conflictsData);
      setRecommendations(recsData);

      if (matchesData.length > 0) {
        // If we navigated here from "Investigate", select + focus that feature.
        const focusFeature = location.state?.focusFeature;
        const focused = focusFeature
          ? matchesData.find((m) => m.feature_a === focusFeature)
          : null;
        if (focused) pendingFocusRef.current = focused;
        const defaultSelected = focused || matchesData.find((m) => m.feature_a === "P-102") || matchesData[0];
        setSelectedMatch(defaultSelected);
      }
      setLoading(false);
    }
    loadData();
  }, []);

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: BASEMAPS.vector,
      center: [77.2100, 28.6140],
      zoom: 16.2,
      pitch: 15,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

    map.on("load", () => {
      mapInstanceRef.current = map;
      setMapReady(true);
    });

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Toggle basemap
  const handleBasemapToggle = (mode) => {
    setBasemapMode(mode);
    const map = mapInstanceRef.current;
    if (!map) return;
    map.setStyle(BASEMAPS[mode], { diff: false });
    map.once("style.load", () => {
      renderVectorLayers(map, matches, selectedMatch);
    });
  };

  // Render vector polygon layers on MapLibre
  const renderVectorLayers = (map, allMatches, currentSelected) => {
    if (!map || !allMatches || allMatches.length === 0) return;

    const cadastralFC = {
      type: "FeatureCollection",
      features: allMatches.map((m) => ({
        type: "Feature",
        id: m.feature_a,
        properties: {
          id: m.feature_a,
          type: "cadastral",
          area: m.feature_a_details?.area,
          owner: m.feature_a_details?.owner,
          land_use: m.feature_a_details?.land_use,
          isSelected: currentSelected?.feature_a === m.feature_a,
        },
        geometry: m.feature_a_details?.geometry,
      })).filter((f) => f.geometry),
    };

    const municipalFC = {
      type: "FeatureCollection",
      features: allMatches.map((m) => ({
        type: "Feature",
        id: m.feature_b,
        properties: {
          id: m.feature_b,
          type: "municipal",
          area: m.feature_b_details?.area,
          zone: m.feature_b_details?.zone,
          address: m.feature_b_details?.address,
          isSelected: currentSelected?.feature_b === m.feature_b,
        },
        geometry: m.feature_b_details?.geometry,
      })).filter((f) => f.geometry),
    };

    if (map.getSource("cadastral-source")) {
      map.getSource("cadastral-source").setData(cadastralFC);
    } else {
      map.addSource("cadastral-source", { type: "geojson", data: cadastralFC });
    }

    if (!map.getLayer("cadastral-fill")) {
      map.addLayer({
        id: "cadastral-fill",
        type: "fill",
        source: "cadastral-source",
        paint: { "fill-color": "#2563eb", "fill-opacity": 0.22 },
      });
      map.addLayer({
        id: "cadastral-line",
        type: "line",
        source: "cadastral-source",
        paint: { "line-color": "#1d4ed8", "line-width": 2.5 },
      });

      map.on("click", "cadastral-fill", (e) => {
        if (e.features && e.features[0]) {
          const fid = e.features[0].properties.id;
          const found = allMatches.find((m) => m.feature_a === fid);
          if (found) selectMatchItem(found);
        }
      });
    }

    if (map.getSource("municipal-source")) {
      map.getSource("municipal-source").setData(municipalFC);
    } else {
      map.addSource("municipal-source", { type: "geojson", data: municipalFC });
    }

    if (!map.getLayer("municipal-fill")) {
      map.addLayer({
        id: "municipal-fill",
        type: "fill",
        source: "municipal-source",
        paint: { "fill-color": "#16a34a", "fill-opacity": 0.2 },
      });
      map.addLayer({
        id: "municipal-line",
        type: "line",
        source: "municipal-source",
        paint: { "line-color": "#16a34a", "line-width": 2, "line-dasharray": [3, 1.5] },
      });

      map.on("click", "municipal-fill", (e) => {
        if (e.features && e.features[0]) {
          const fid = e.features[0].properties.id;
          const found = allMatches.find((m) => m.feature_b === fid);
          if (found) selectMatchItem(found);
        }
      });
    }

    // Selected Feature Focus Highlight
    const selectedGeom = currentSelected?.feature_a_details?.geometry;
    const highlightFC = {
      type: "FeatureCollection",
      features: selectedGeom
        ? [{ type: "Feature", properties: {}, geometry: selectedGeom }]
        : [],
    };

    if (map.getSource("highlight-source")) {
      map.getSource("highlight-source").setData(highlightFC);
    } else {
      map.addSource("highlight-source", { type: "geojson", data: highlightFC });
    }

    if (!map.getLayer("highlight-line")) {
      map.addLayer({
        id: "highlight-line",
        type: "line",
        source: "highlight-source",
        paint: { "line-color": "#dc2626", "line-width": 3.5 },
      });
    }

    if (map.getLayer("cadastral-fill")) {
      map.setLayoutProperty("cadastral-fill", "visibility", layersVisibility.cadastral ? "visible" : "none");
      map.setLayoutProperty("cadastral-line", "visibility", layersVisibility.cadastral ? "visible" : "none");
    }
    if (map.getLayer("municipal-fill")) {
      map.setLayoutProperty("municipal-fill", "visibility", layersVisibility.municipal ? "visible" : "none");
      map.setLayoutProperty("municipal-line", "visibility", layersVisibility.municipal ? "visible" : "none");
    }
  };

  // One-time auto-fit to the full extent, only when the map AND data are first
  // both ready. Guarded by hasFittedRef and skipped when we arrived via
  // "Investigate" (pendingFocusRef) — so a later Inspect click is never
  // overridden by a zoom-out.
  useEffect(() => {
    if (!mapReady || !mapInstanceRef.current || hasFittedRef.current) return;
    if (matches.length === 0) return;

    const map = mapInstanceRef.current;
    hasFittedRef.current = true; // Mark as fitted no matter what

    // If we're going to focus a specific feature shortly, do NOT run the full-extent fit.
    if (pendingFocusRef.current) {
      return;
    }

    try {
      const allCoords = matches.flatMap((m) => m.feature_a_details?.geometry?.coordinates[0] || []);
      if (allCoords.length > 0) {
        const bounds = allCoords.reduce(
          (b, coord) => b.extend(coord),
          new maplibregl.LngLatBounds(allCoords[0], allCoords[0])
        );
        map.fitBounds(bounds, { padding: 60, maxZoom: 17, duration: 800 });
      }
    } catch (e) {
      console.error("Auto-fit to features failed:", e);
    }
  }, [mapReady, matches]);

  // Re-render layers on data/selection change; if we landed via "Investigate",
  // zoom the camera to that specific match's polygon.
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !map.isStyleLoaded()) return;
    renderVectorLayers(map, matches, selectedMatch);

    if (pendingFocusRef.current) {
      const focus = pendingFocusRef.current;
      pendingFocusRef.current = null;
      try {
        const coords = focus.feature_a_details?.geometry?.coordinates[0];
        if (coords && coords.length) {
          const bounds = coords.reduce(
            (b, c) => b.extend(c),
            new maplibregl.LngLatBounds(coords[0], coords[0])
          );
          map.fitBounds(bounds, { padding: 90, maxZoom: 18, duration: 800 });
        }
      } catch (e) {
        console.error("Focus zoom failed:", e);
      }
    }
  }, [matches, selectedMatch, layersVisibility, mapReady]);

  // Select match item and synchronize Map ↔ Table ↔ Investigation Panel
  const selectMatchItem = (match) => {
    setSelectedMatch(match);
    setReviewMessage(null);

    const map = mapInstanceRef.current;
    if (!map || !match.feature_a_details?.geometry) return;

    try {
      const coords = match.feature_a_details.geometry.coordinates[0];
      const bounds = coords.reduce(
        (b, coord) => b.extend(coord),
        new maplibregl.LngLatBounds(coords[0], coords[0])
      );
      map.fitBounds(bounds, { padding: 90, maxZoom: 17.5, duration: 750 });
    } catch (e) {
      console.error("Zoom to feature failed:", e);
    }
  };

  const handleFitAll = () => {
    const map = mapInstanceRef.current;
    if (!map || matches.length === 0) return;
    try {
      const allCoords = matches.flatMap((m) => m.feature_a_details?.geometry?.coordinates[0] || []);
      if (allCoords.length > 0) {
        const bounds = allCoords.reduce(
          (b, coord) => b.extend(coord),
          new maplibregl.LngLatBounds(allCoords[0], allCoords[0])
        );
        map.fitBounds(bounds, { padding: 60, duration: 800 });
      }
    } catch (e) {
      console.error("Fit all failed:", e);
    }
  };

  // Review Decision Submission
  const handleReviewDecision = async (decision, commentText = null) => {
    if (!selectedMatch) return;
    const matchingConflict = conflicts.find((c) => c.feature_a === selectedMatch.feature_a) || { id: 1 };

    await api.submitReview(matchingConflict.id, {
      decision,
      reviewer: "Cadastral Officer",
      comment: commentText || (decision === "accept" ? "Accepted recommended cadastral alignment." : "Decision updated by officer."),
    });

    setReviewMessage({
      type: decision === "accept" ? "success" : "info",
      text: `Decision "${decision.toUpperCase()}" recorded for Parcel ${selectedMatch.feature_a}.`,
    });

    setConflicts((prev) =>
      prev.map((c) =>
        c.id === matchingConflict.id
          ? { ...c, status: decision === "accept" ? "resolved" : "flagged" }
          : c
      )
    );
    setEditDecisionModal(false);
  };

  const filteredMatches = matches.filter((m) => {
    if (filter === "matched" && m.status !== "matched") return false;
    if (filter === "review" && m.status !== "review") return false;
    if (filter === "conflict") {
      const hasConflict = conflicts.some((c) => c.feature_a === m.feature_a && c.status !== "resolved");
      if (!hasConflict) return false;
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchA = m.feature_a.toLowerCase().includes(q);
      const matchB = m.feature_b.toLowerCase().includes(q);
      const matchOwner = (m.feature_a_details?.owner || "").toLowerCase().includes(q);
      if (!matchA && !matchB && !matchOwner) return false;
    }
    return true;
  });

  const activeConflict = selectedMatch
    ? conflicts.find((c) => c.feature_a === selectedMatch.feature_a)
    : null;

  const activeRecommendation = selectedMatch
    ? recommendations.find((r) => r.feature_a === selectedMatch.feature_a)
    : null;

  const pendingConflictsCount = conflicts.filter((c) => c.status !== "resolved").length;
  const pendingReviewCount = matches.filter((m) => m.status === "review").length;

  return (
    <div className="content-full">
      <div className="workspace-container">
        {/* Top Workspace Toolbar */}
        <div className="workspace-top-toolbar">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontWeight: "700", fontSize: "13px", color: "var(--text-primary)" }}>
              Harmonization Workspace
            </span>
            <span style={{ color: "var(--border-strong)" }}>|</span>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              {loading ? "Loading..." : `${matches.length} Feature Pair${matches.length !== 1 ? "s" : ""} · ${pendingConflictsCount} Conflict${pendingConflictsCount !== 1 ? "s" : ""}`}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button className="btn btn-secondary btn-sm" onClick={handleFitAll}>
              <IconMaximize size={13} />
              Fit Extent
            </button>
            <div className="filter-chip-group">
              <button
                className={`filter-chip ${basemapMode === "vector" ? "active" : ""}`}
                onClick={() => handleBasemapToggle("vector")}
              >
                Vector
              </button>
              <button
                className={`filter-chip ${basemapMode === "satellite" ? "active" : ""}`}
                onClick={() => handleBasemapToggle("satellite")}
              >
                Satellite (Esri)
              </button>
            </div>
          </div>
        </div>

        {/* 3-Column Workspace Distribution */}
        <div className="workspace-body">
          {/* Left Panel: Layers & Filters (15%) */}
          <aside className="workspace-left-panel">
            <div className="panel-section">
              <div className="panel-section-title">
                <span>Layers</span>
                <span style={{ fontSize: "10px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>EPSG:4326</span>
              </div>

              <div className="layer-item">
                <div className="layer-item-left">
                  <input
                    type="checkbox"
                    checked={layersVisibility.cadastral}
                    onChange={(e) => setLayersVisibility({ ...layersVisibility, cadastral: e.target.checked })}
                    id="layer-cadastral"
                  />
                  <span className="layer-color-chip layer-cadastral"></span>
                  <label htmlFor="layer-cadastral" style={{ cursor: "pointer", fontSize: "12.5px", fontWeight: "600" }}>
                    Cadastral Survey
                  </label>
                </div>
                <span className="badge badge-info">Source A</span>
              </div>

              <div className="layer-item">
                <div className="layer-item-left">
                  <input
                    type="checkbox"
                    checked={layersVisibility.municipal}
                    onChange={(e) => setLayersVisibility({ ...layersVisibility, municipal: e.target.checked })}
                    id="layer-municipal"
                  />
                  <span className="layer-color-chip layer-municipal"></span>
                  <label htmlFor="layer-municipal" style={{ cursor: "pointer", fontSize: "12.5px", fontWeight: "600" }}>
                    Municipal GIS
                  </label>
                </div>
                <span className="badge badge-info">Source B</span>
              </div>
            </div>

            <div className="panel-section">
              <div className="panel-section-title">
                <span>Filters</span>
              </div>

              <div style={{ marginBottom: "10px" }}>
                <div style={{ position: "relative" }}>
                  <input
                    type="text"
                    placeholder="Search Parcel ID..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "6px 8px 6px 26px",
                      borderRadius: "var(--radius-sm)",
                      border: "1px solid var(--border-subtle)",
                      fontSize: "12px",
                    }}
                  />
                  <span style={{ position: "absolute", left: "8px", top: "7px", color: "var(--text-muted)" }}>
                    <IconSearch size={13} />
                  </span>
                </div>
              </div>

              <div className="filter-chip-group">
                <button className={`filter-chip ${filter === "all" ? "active" : ""}`} onClick={() => setFilter("all")}>
                  All ({matches.length})
                </button>
                <button className={`filter-chip ${filter === "matched" ? "active" : ""}`} onClick={() => setFilter("matched")}>
                  Matched ({matches.filter((m) => m.status === "matched").length})
                </button>
                <button className={`filter-chip ${filter === "review" ? "active" : ""}`} onClick={() => setFilter("review")}>
                  Review ({matches.filter((m) => m.status === "review").length})
                </button>
                <button className={`filter-chip ${filter === "conflict" ? "active" : ""}`} onClick={() => setFilter("conflict")}>
                  Conflicts ({conflicts.filter((c) => c.status !== "resolved").length})
                </button>
              </div>
            </div>
          </aside>

          {/* Center: Large Map Canvas (55-65%) */}
          <main className="workspace-map-center">
            <div ref={mapContainerRef} className="map-canvas-container" />

            <div className="map-floating-legend">
              <div style={{ fontWeight: "700", marginBottom: "4px", fontSize: "11px", textTransform: "uppercase" }}>
                Layer Symbology
              </div>
              <div className="legend-row">
                <span className="legend-box" style={{ background: "#2563eb" }}></span>
                <span>Cadastral Survey (Primary)</span>
              </div>
              <div className="legend-row">
                <span className="legend-box" style={{ background: "#16a34a" }}></span>
                <span>Municipal GIS (MCD)</span>
              </div>
            </div>
          </main>

          {/* Right Panel: Progressive Disclosure Investigation (25-30%) */}
          <aside className="workspace-right-panel">
            {selectedMatch ? (
              <>
                <div className="right-panel-header">
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "2px" }}>
                      <h3 style={{ fontSize: "15px", fontWeight: "700" }}>{selectedMatch.feature_a}</h3>
                      <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>↔</span>
                      <h3 style={{ fontSize: "15px", fontWeight: "700" }}>{selectedMatch.feature_b}</h3>
                    </div>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      Cadastral vs Municipal Cross-Reference
                    </span>
                  </div>

                  <span className={`badge ${selectedMatch.status === "matched" ? "badge-matched" : "badge-review"}`}>
                    {selectedMatch.status === "matched" ? "High Agreement" : "Review Required"}
                  </span>
                </div>

                <div className="right-panel-content">
                  {reviewMessage && (
                    <div style={{ padding: "8px 10px", borderRadius: "var(--radius-sm)", background: "var(--color-success-bg)", color: "var(--color-success-text)", border: "1px solid var(--color-success-border)", fontSize: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <IconCheck size={14} />
                      <span>{reviewMessage.text}</span>
                    </div>
                  )}

                  {/* Confidence Summary & Expandable Evidence */}
                  <div className="confidence-gauge-box">
                    <div className="gauge-header">
                      <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-secondary)" }}>
                        Confidence Score
                      </span>
                      <span className="gauge-score">{selectedMatch.score}%</span>
                    </div>

                    <div className="gauge-bar-track">
                      <div className="gauge-bar-fill" style={{ width: `${selectedMatch.score}%` }}></div>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <button
                        style={{ border: "none", background: "none", color: "var(--primary-blue)", cursor: "pointer", fontSize: "11.5px", fontWeight: "600", padding: 0 }}
                        onClick={() => setEvidenceExpanded(!evidenceExpanded)}
                      >
                        {evidenceExpanded ? "Hide Evidence ↑" : "View Evidence Breakdown ↓"}
                      </button>
                    </div>

                    {evidenceExpanded && (
                      <div className="component-bars" style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                        <div className="component-row">
                          <span>Geometry IoU Overlap:</span>
                          <strong style={{ fontFamily: "var(--font-mono)" }}>
                            {selectedMatch.breakdown?.components?.geometry ? Math.round(selectedMatch.breakdown.components.geometry * 100) : 86}%
                          </strong>
                        </div>
                        <div className="component-row">
                          <span>Centroid Proximity:</span>
                          <strong style={{ fontFamily: "var(--font-mono)" }}>
                            {selectedMatch.breakdown?.components?.proximity ? Math.round(selectedMatch.breakdown.components.proximity * 100) : 94}%
                          </strong>
                        </div>
                        <div className="component-row">
                          <span>Area Proportion Ratio:</span>
                          <strong style={{ fontFamily: "var(--font-mono)" }}>
                            {selectedMatch.breakdown?.components?.area ? Math.round(selectedMatch.breakdown.components.area * 100) : 90}%
                          </strong>
                        </div>
                        <div className="component-row">
                          <span>Source Reliability:</span>
                          <strong style={{ fontFamily: "var(--font-mono)" }}>
                            {selectedMatch.breakdown?.components?.reliability ? Math.round(selectedMatch.breakdown.components.reliability * 100) : 92}%
                          </strong>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Attribute Comparison */}
                  <div>
                    <div style={{ fontSize: "11px", fontWeight: "700", marginBottom: "6px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
                      Attribute Comparison
                    </div>
                    <table className="comparison-table">
                      <thead>
                        <tr>
                          <th>Attribute</th>
                          <th>Cadastral (A)</th>
                          <th>Municipal (B)</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td><strong>Feature ID</strong></td>
                          <td>{selectedMatch.feature_a}</td>
                          <td>{selectedMatch.feature_b}</td>
                        </tr>
                        <tr>
                          <td><strong>Area</strong></td>
                          <td>{selectedMatch.feature_a_details?.area ? `${selectedMatch.feature_a_details.area} m²` : "1,240 m²"}</td>
                          <td>
                            {selectedMatch.feature_b_details?.area ? `${selectedMatch.feature_b_details.area} m²` : "1,256 m²"}
                            {activeConflict?.type === "area" && <span className="diff-alert">Δ 16 m²</span>}
                          </td>
                        </tr>
                        <tr>
                          <td><strong>Classification</strong></td>
                          <td>{selectedMatch.feature_a_details?.land_use || "Residential"}</td>
                          <td>{selectedMatch.feature_b_details?.zone || "Zone R-2"}</td>
                        </tr>
                        <tr>
                          <td><strong>Owner / Addr</strong></td>
                          <td>{selectedMatch.feature_a_details?.owner || "Ramesh Sharma"}</td>
                          <td>{selectedMatch.feature_b_details?.address || "Plot 102, Sec 14"}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Conflict Notice */}
                  {activeConflict && (
                    <div className="conflict-card">
                      <div className="conflict-card-header">
                        <span>Discrepancy: {activeConflict.type.toUpperCase()}</span>
                        <span className="badge badge-danger">{activeConflict.severity}</span>
                      </div>
                      <div className="conflict-card-body">{activeConflict.reason}</div>
                    </div>
                  )}

                  {/* AI Recommendation Card */}
                  <div className="recommendation-card">
                    <div className="recommendation-header">
                      <span className="recommendation-title">RECOMMENDATION</span>
                      <span className="badge badge-info">Confidence: {activeRecommendation?.confidence || 89}%</span>
                    </div>

                    <div className="recommendation-action-badge">
                      {activeRecommendation?.action === "prefer_source"
                        ? "Action: prefer_source (Cadastral Baseline)"
                        : "Action: merge_attributes"}
                    </div>

                    <p className="recommendation-reason">
                      {activeRecommendation?.reason || "State Revenue Survey has established legal ground truth and higher reliability (0.95 vs 0.82)."}
                    </p>

                    <div className="decision-buttons">
                      <button className="btn btn-success btn-sm" onClick={() => handleReviewDecision("accept")}>
                        Accept
                      </button>
                      <button className="btn btn-secondary btn-sm" onClick={() => setEditDecisionModal(true)}>
                        Edit
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleReviewDecision("reject")}>
                        Reject
                      </button>
                    </div>
                  </div>

                  {editDecisionModal && (
                    <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-strong)", borderRadius: "var(--radius-md)", padding: "10px", boxShadow: "var(--shadow-md)" }}>
                      <label style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                        Override Comment:
                      </label>
                      <textarea
                        rows={2}
                        value={customComment}
                        onChange={(e) => setCustomComment(e.target.value)}
                        placeholder="Reason for decision override..."
                        style={{ width: "100%", padding: "5px", fontSize: "12px", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", marginBottom: "6px" }}
                      />
                      <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => setEditDecisionModal(false)}>Cancel</button>
                        <button className="btn btn-primary btn-sm" onClick={() => handleReviewDecision("edit", customComment)}>Save</button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ padding: "40px 20px", textAlign: "center", color: "var(--text-muted)" }}>
                Select a parcel row from the queue to inspect cross-source evidence.
              </div>
            )}
          </aside>
        </div>

        {/* Collapsible Match Queue Drawer */}
        <footer className={`workspace-bottom-panel ${queueOpen ? "expanded" : "collapsed"}`}>
          <div className="queue-header" onClick={() => setQueueOpen(!queueOpen)}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span>
                {filteredMatches.length} Match Candidates · {pendingConflictsCount} Conflicts · {pendingReviewCount} Pending Review
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                (Click row to zoom map & inspect evidence)
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                {queueOpen ? "Collapse Queue" : "Expand Queue Table"}
              </span>
              {queueOpen ? <IconChevronDown size={14} /> : <IconChevronUp size={14} />}
            </div>
          </div>

          {queueOpen && (
            <div className="queue-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Feature (A)</th>
                    <th>Candidate (B)</th>
                    <th>Confidence</th>
                    <th>Geometry</th>
                    <th>Area</th>
                    <th>Classification</th>
                    <th>Conflict</th>
                    <th>Recommendation</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMatches.map((m) => {
                    const conf = conflicts.find((c) => c.feature_a === m.feature_a);
                    const rec = recommendations.find((r) => r.feature_a === m.feature_a);
                    const isSelected = selectedMatch?.feature_a === m.feature_a;

                    return (
                      <tr
                        key={m.feature_a}
                        className={isSelected ? "selected" : ""}
                        onClick={() => selectMatchItem(m)}
                        style={{ cursor: "pointer" }}
                      >
                        <td><strong>{m.feature_a}</strong></td>
                        <td>{m.feature_b}</td>
                        <td><strong style={{ fontFamily: "var(--font-mono)" }}>{m.score}%</strong></td>
                        <td>{Math.round((m.breakdown?.components?.geometry || 0.86) * 100)}%</td>
                        <td>{Math.round((m.breakdown?.components?.area || 0.90) * 100)}%</td>
                        <td>{m.feature_a_details?.land_use || "Residential"}</td>
                        <td>
                          {conf ? <span className="badge badge-conflict">{conf.type}</span> : <span style={{ color: "var(--text-muted)" }}>None</span>}
                        </td>
                        <td style={{ fontSize: "11.5px" }}>{rec?.action === "prefer_source" ? "Prefer Cadastral" : "Merge Attributes"}</td>
                        <td>
                          {conf?.status === "resolved" ? (
                            <span className="badge badge-resolved">Resolved</span>
                          ) : m.status === "matched" ? (
                            <span className="badge badge-matched">Auto-Matched</span>
                          ) : (
                            <span className="badge badge-review">Review</span>
                          )}
                        </td>
                        <td>
                          <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); selectMatchItem(m); }}>
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </footer>
      </div>
    </div>
  );
}
