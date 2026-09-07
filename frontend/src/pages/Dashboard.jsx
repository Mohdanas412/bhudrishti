import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api } from "../services/api";
import {
  IconWorkspace,
  IconLayers,
  IconAlertCircle,
  IconCheckCircle,
  IconArrowRight,
  IconDataSources
} from "../components/Icons";

const BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

export default function Dashboard() {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);

  const [datasets, setDatasets] = useState([]);
  const [matches, setMatches] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);

  const [layersVisibility, setLayersVisibility] = useState({
    cadastral: true,
    municipal: true,
    conflicts: true,
  });

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      const [d, m, c] = await Promise.all([
        api.getDatasets(),
        api.getMatches(),
        api.getConflicts(),
      ]);
      setDatasets(d);
      setMatches(m);
      setConflicts(c);
      setLoading(false);
    }
    fetchData();
  }, []);

  // Initialize MapLibre Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: BASEMAP_STYLE,
      center: [77.2100, 28.6140],
      zoom: 15.6,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

    map.on("load", () => {
      mapInstanceRef.current = map;
      renderMapFeatures(map, matches, conflicts);
    });

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  const renderMapFeatures = (map, allMatches, allConflicts) => {
    if (!map || !allMatches || allMatches.length === 0) return;

    const cadFeatures = allMatches
      .filter((m) => m.feature_a_details?.geometry)
      .map((m) => ({
        type: "Feature",
        id: m.feature_a,
        properties: { id: m.feature_a, type: "cadastral" },
        geometry: m.feature_a_details.geometry,
      }));

    const munFeatures = allMatches
      .filter((m) => m.feature_b_details?.geometry)
      .map((m) => ({
        type: "Feature",
        id: m.feature_b,
        properties: { id: m.feature_b, type: "municipal" },
        geometry: m.feature_b_details.geometry,
      }));

    const confFeatures = allConflicts
      .filter((c) => c.feature_a_details?.geometry && c.status !== "resolved")
      .map((c) => ({
        type: "Feature",
        id: `conf-${c.id}`,
        properties: { id: c.id, reason: c.reason },
        geometry: c.feature_a_details.geometry,
      }));

    // Add Cadastral
    if (map.getSource("dash-cadastral")) {
      map.getSource("dash-cadastral").setData({ type: "FeatureCollection", features: cadFeatures });
    } else {
      map.addSource("dash-cadastral", { type: "geojson", data: { type: "FeatureCollection", features: cadFeatures } });
      map.addLayer({
        id: "dash-cadastral-fill",
        type: "fill",
        source: "dash-cadastral",
        paint: { "fill-color": "#2563eb", "fill-opacity": 0.2 },
      });
      map.addLayer({
        id: "dash-cadastral-line",
        type: "line",
        source: "dash-cadastral",
        paint: { "line-color": "#1d4ed8", "line-width": 2 },
      });
    }

    // Add Municipal
    if (map.getSource("dash-municipal")) {
      map.getSource("dash-municipal").setData({ type: "FeatureCollection", features: munFeatures });
    } else {
      map.addSource("dash-municipal", { type: "geojson", data: { type: "FeatureCollection", features: munFeatures } });
      map.addLayer({
        id: "dash-municipal-fill",
        type: "fill",
        source: "dash-municipal",
        paint: { "fill-color": "#16a34a", "fill-opacity": 0.2 },
      });
      map.addLayer({
        id: "dash-municipal-line",
        type: "line",
        source: "dash-municipal",
        paint: { "line-color": "#16a34a", "line-width": 1.8, "line-dasharray": [3, 2] },
      });
    }

    // Add Conflicts
    if (map.getSource("dash-conflicts")) {
      map.getSource("dash-conflicts").setData({ type: "FeatureCollection", features: confFeatures });
    } else {
      map.addSource("dash-conflicts", { type: "geojson", data: { type: "FeatureCollection", features: confFeatures } });
      map.addLayer({
        id: "dash-conflict-line",
        type: "line",
        source: "dash-conflicts",
        paint: { "line-color": "#dc2626", "line-width": 3.5 },
      });
    }
  };

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (map.getLayer("dash-cadastral-fill")) {
      map.setLayoutProperty("dash-cadastral-fill", "visibility", layersVisibility.cadastral ? "visible" : "none");
      map.setLayoutProperty("dash-cadastral-line", "visibility", layersVisibility.cadastral ? "visible" : "none");
    }
    if (map.getLayer("dash-municipal-fill")) {
      map.setLayoutProperty("dash-municipal-fill", "visibility", layersVisibility.municipal ? "visible" : "none");
      map.setLayoutProperty("dash-municipal-line", "visibility", layersVisibility.municipal ? "visible" : "none");
    }
    if (map.getLayer("dash-conflict-line")) {
      map.setLayoutProperty("dash-conflict-line", "visibility", layersVisibility.conflicts ? "visible" : "none");
    }
  }, [layersVisibility]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (map && map.isStyleLoaded()) {
      renderMapFeatures(map, matches, conflicts);
    }
  }, [matches, conflicts]);

  const matchedCount = matches.filter((m) => m.status === "matched").length;
  const reviewCount = matches.filter((m) => m.status === "review").length;
  const activeConflicts = conflicts.filter((c) => c.status !== "resolved");

  return (
    <div className="content">
      <div className="content-wrapper">
        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">BhuDrishti Overview</h1>
            <p className="page-subtitle">
              Monitor datasets, spatial coverage, harmonization progress, and officer review priorities.
            </p>
          </div>

          <div className="header-actions">
            <Link to="/workspace" className="btn btn-primary">
              <IconWorkspace size={16} />
              Open Harmonization Workspace
            </Link>
          </div>
        </div>

        {/* Compact Metric Summary Row */}
        <div className="dashboard-metrics-row">
          <div className="metric-box-compact">
            <div className="metric-box-title">Data Sources</div>
            <div className="metric-box-value">{loading ? "–" : datasets.length}</div>
          </div>

          <div className="metric-box-compact">
            <div className="metric-box-title">Feature Pairs</div>
            <div className="metric-box-value">{loading ? "–" : matches.length}</div>
          </div>

          <div className="metric-box-compact">
            <div className="metric-box-title">Auto-Matched</div>
            <div className="metric-box-value" style={{ color: loading ? "var(--text-muted)" : "var(--color-success)" }}>
              {loading ? "–" : matchedCount}
            </div>
          </div>

          <div className="metric-box-compact">
            <div className="metric-box-title">Needs Review</div>
            <div className="metric-box-value" style={{ color: loading ? "var(--text-muted)" : reviewCount > 0 ? "var(--color-warning)" : "var(--color-success)" }}>
              {loading ? "–" : reviewCount}
            </div>
          </div>

          <div className="metric-box-compact">
            <div className="metric-box-title">Conflicts</div>
            <div className="metric-box-value" style={{ color: loading ? "var(--text-muted)" : activeConflicts.length > 0 ? "var(--color-danger)" : "var(--color-success)" }}>
              {loading ? "–" : activeConflicts.length}
            </div>
          </div>
        </div>

        {/* Primary Map Section (60–70% Visual Importance) */}
        <div className="dashboard-map-container">
          <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />

          {/* Floating Light Layer Switcher on Map */}
          <div style={{ position: "absolute", top: "14px", left: "14px", background: "rgba(255, 255, 255, 0.95)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "10px 14px", boxShadow: "var(--shadow-md)", zIndex: 10, fontSize: "12px" }}>
            <div style={{ fontWeight: 700, fontSize: "11px", textTransform: "uppercase", color: "var(--text-secondary)", marginBottom: "6px" }}>
              Coverage Layers
            </div>
            <div style={{ display: "flex", gap: "14px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={layersVisibility.cadastral}
                  onChange={(e) => setLayersVisibility({ ...layersVisibility, cadastral: e.target.checked })}
                />
                <span className="layer-color-chip layer-cadastral"></span>
                <span>Cadastral Survey</span>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={layersVisibility.municipal}
                  onChange={(e) => setLayersVisibility({ ...layersVisibility, municipal: e.target.checked })}
                />
                <span className="layer-color-chip layer-municipal"></span>
                <span>Municipal GIS</span>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={layersVisibility.conflicts}
                  onChange={(e) => setLayersVisibility({ ...layersVisibility, conflicts: e.target.checked })}
                />
                <span className="layer-color-chip" style={{ background: "var(--layer-conflict)" }}></span>
                <span>Hotspots</span>
              </label>
            </div>
          </div>
        </div>

        {/* Content Below Map (NATURAL PAGE SCROLLING) */}
        <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr", gap: "24px", marginBottom: "24px" }}>
          {/* Priority Review Priorities Table */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Priority Discrepancy Review</span>
              <Link to="/conflicts" className="btn btn-secondary btn-sm">
                View All ({conflicts.length})
              </Link>
            </div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Conflict ID</th>
                    <th>Source A</th>
                    <th>Source B</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {conflicts.slice(0, 3).map((c) => (
                    <tr key={c.id}>
                      <td><strong>#C-{c.id}</strong></td>
                      <td>{c.feature_a}</td>
                      <td>{c.feature_b}</td>
                      <td><span className="badge badge-conflict">{c.type}</span></td>
                      <td><span className="badge badge-warning">{c.severity}</span></td>
                      <td>
                        <Link to="/workspace" className="btn btn-secondary btn-sm">
                          Resolve <IconArrowRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Active Data Sources Summary */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Active Data Sources</span>
              <Link to="/datasets" className="btn btn-secondary btn-sm">
                Manage Sources
              </Link>
            </div>
            <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {datasets.map((d) => (
                <div key={d.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", background: "var(--bg-surface-subtle)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)" }}>
                  <div>
                    <div style={{ fontWeight: "700", fontSize: "12.5px" }}>{d.filename}</div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{d.source_name || "Official Registry"}</div>
                  </div>
                  <span className="badge badge-standardized">{d.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
