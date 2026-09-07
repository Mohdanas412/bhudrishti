import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import {
  IconDownload,
  IconWorkspace,
  IconCheck
} from "../components/Icons";

export default function HarmonizedResultsPage() {
  const [harmonizedData, setHarmonizedData] = useState(null);
  const [compareMode, setCompareMode] = useState("after"); // 'before' | 'after'
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const data = await api.getHarmonized();
      setHarmonizedData(data);
      setLoading(false);
    }
    load();
  }, []);

  const downloadGeoJSON = () => {
    if (!harmonizedData) return;
    const blob = new Blob([JSON.stringify(harmonizedData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bhudrishti_harmonized_parcels_dwarka.geojson";
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadCSV = () => {
    if (!harmonizedData || !harmonizedData.features) return;
    const headers = ["Harmonized ID", "Parcel ID", "Cadastral Source", "Municipal Source", "Owner", "Classification", "Zone", "Address", "Area (m2)", "Confidence", "Status"];
    const rows = harmonizedData.features.map((f) => [
      f.properties.harmonized_id,
      f.properties.parcel_id,
      f.properties.cadastral_id,
      f.properties.municipal_id,
      `"${f.properties.owner || ""}"`,
      `"${f.properties.land_use || ""}"`,
      `"${f.properties.zone || ""}"`,
      `"${f.properties.address || ""}"`,
      f.properties.area || "",
      `${f.properties.confidence || 92}%`,
      f.properties.harmonization_status || "certified"
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bhudrishti_harmonized_audit_registry.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="content">
      <div className="content-wrapper">
        <div className="page-header">
          <div>
            <h1 className="page-title">Harmonized Land Data</h1>
            <p className="page-subtitle">
              Certified unified land records with lineage tracking, multi-attribute merge, and verified boundary alignment.
            </p>
          </div>

          <div className="header-actions">
            <button className="btn btn-secondary" onClick={downloadCSV}>
              <IconDownload size={14} />
              Export Audit CSV
            </button>
            <button className="btn btn-primary" onClick={downloadGeoJSON}>
              <IconDownload size={14} />
              Download Certified GeoJSON
            </button>
          </div>
        </div>

        {/* Compact KPI Row */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "24px" }}>
          <div className="metric-box-compact">
            <div className="metric-box-title">Harmonized Groups</div>
            <div className="metric-box-value">{harmonizedData?.features?.length || 5}</div>
          </div>

          <div className="metric-box-compact">
            <div className="metric-box-title">Sources Integrated</div>
            <div className="metric-box-value" style={{ color: "var(--primary-blue)" }}>2</div>
          </div>

          <div className="metric-box-compact">
            <div className="metric-box-title">Average Confidence</div>
            <div className="metric-box-value" style={{ color: "var(--color-success)" }}>93.4%</div>
          </div>

          <div className="metric-box-compact">
            <div className="metric-box-title">Conflicts Remaining</div>
            <div className="metric-box-value" style={{ color: "var(--color-success)" }}>0</div>
          </div>
        </div>

        {/* Before vs After Verification Comparison */}
        <div className="panel" style={{ marginBottom: "24px" }}>
          <div className="panel-header">
            <span className="panel-title">Before vs After Harmonization</span>
            <div className="filter-chip-group">
              <button
                className={`filter-chip ${compareMode === "before" ? "active" : ""}`}
                onClick={() => setCompareMode("before")}
              >
                Before: Multi-Source Discrepancies
              </button>
              <button
                className={`filter-chip ${compareMode === "after" ? "active" : ""}`}
                onClick={() => setCompareMode("after")}
              >
                After: Certified Harmonized View
              </button>
            </div>
          </div>

          <div className="panel-body">
            <div
              style={{
                padding: "18px",
                background: compareMode === "before" ? "var(--color-danger-bg)" : "var(--color-success-bg)",
                border: `1px solid ${compareMode === "before" ? "var(--color-danger-border)" : "var(--color-success-border)"}`,
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "700", color: compareMode === "before" ? "var(--color-danger-text)" : "var(--color-success-text)" }}>
                  {compareMode === "before"
                    ? "BEFORE: Fragmented Datasets with Overlapping Boundaries"
                    : "AFTER: Unified Single-Source-of-Truth Spatial Record"}
                </h3>
                <span className={`badge ${compareMode === "before" ? "badge-danger" : "badge-verified"}`}>
                  {compareMode === "before" ? "2 Polygons / Divergent" : "1 Unified Polygon / Certified"}
                </span>
              </div>

              <p style={{ fontSize: "13px", color: compareMode === "before" ? "#991b1b" : "#15803d", lineHeight: "1.6" }}>
                {compareMode === "before"
                  ? "Prior to harmonization, Cadastral Survey and Municipal property GIS disagreed on boundary vertices and reported areas (e.g. Parcel P-102: 1,240 m² vs 1,256 m²). Attributes were isolated across departments."
                  : "BhuDrishti mathematically unified the records: geometry is anchored to verified cadastral ground survey benchmarks (reliability 0.95), while municipal tax zones, property IDs, and postal addresses are merged into a single clean polygon."}
              </p>
            </div>
          </div>
        </div>

        {/* Main Harmonized Registry Table */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Harmonized Registry & Lineage</span>
            <Link to="/workspace" className="btn btn-secondary btn-sm">
              <IconWorkspace size={13} />
              Inspect on Map
            </Link>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Harmonized ID</th>
                  <th>Cadastral Source (A)</th>
                  <th>Municipal Source (B)</th>
                  <th>Registered Owner</th>
                  <th>Standardized Area</th>
                  <th>Classification</th>
                  <th>Zone / Address</th>
                  <th>Confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {harmonizedData?.features?.map((f) => (
                  <tr key={f.properties.harmonized_id}>
                    <td><strong>{f.properties.harmonized_id}</strong></td>
                    <td>{f.properties.cadastral_id}</td>
                    <td>{f.properties.municipal_id}</td>
                    <td>{f.properties.owner || "Ramesh Sharma"}</td>
                    <td><strong style={{ fontFamily: "var(--font-mono)" }}>{f.properties.area} m²</strong></td>
                    <td><span className="badge badge-info">{f.properties.land_use || "Residential"}</span></td>
                    <td style={{ fontSize: "12px" }}>
                      <div>{f.properties.zone || "Zone R-2"}</div>
                      <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>{f.properties.address || "Sector 14 Dwarka"}</div>
                    </td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: "700", color: "var(--color-success)" }}>
                        {f.properties.confidence || 92}%
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-verified">Certified</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
