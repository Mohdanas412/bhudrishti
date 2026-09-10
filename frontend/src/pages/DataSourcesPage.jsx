import React, { useEffect, useState } from "react";
import { api } from "../services/api";
import {
  IconUpload,
  IconCheck,
  IconAlertCircle,
  IconRefresh
} from "../components/Icons";

export default function DataSourcesPage() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState("cadastral");
  const [uploadFile, setUploadFile] = useState(null);
  const [processingId, setProcessingId] = useState(null);
  const [actionOutput, setActionOutput] = useState(null);

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    setLoading(true);
    const data = await api.getDatasets();
    setDatasets(data);
    setLoading(false);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    try {
      setLoading(true);
      const res = await api.uploadDataset(uploadFile, selectedType);
      setUploadFile(null);
      await loadDatasets();
      setActionOutput({
        type: "success",
        title: "Dataset Registered",
        text: `File "${uploadFile.name}" registered cleanly as ${selectedType.toUpperCase()} (ID #${res.id}).`
      });
    } catch (err) {
      setActionOutput({
        type: "error",
        title: "Upload Failed",
        text: err.message
      });
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async (id) => {
    setProcessingId(id);
    const res = await api.validateDataset(id);
    setProcessingId(null);
    setActionOutput({
      type: res.valid ? "success" : "warning",
      title: res.valid ? "Validation Passed" : "Geometry Issues Found",
      text: res.valid
        ? `Dataset #${id} CRS and geometry verified cleanly.`
        : `Dataset #${id} contains ${res.issues?.length || 0} issue(s).`,
      details: res.issues
    });
    await loadDatasets();
  };

  const handleStandardize = async (id) => {
    setProcessingId(id);
    const res = await api.standardizeDataset(id);
    setProcessingId(null);
    setActionOutput({
      type: "success",
      title: "Schema Standardized",
      text: `Dataset #${id} reprojected to EPSG:4326 and canonical fields mapped via rapidfuzz.`,
    });
    await loadDatasets();
  };

  const handleRepair = async (id) => {
    setProcessingId(id);
    const res = await api.repairDataset(id);
    setProcessingId(null);
    setActionOutput({
      type: "success",
      title: "Topology Repaired",
      text: `Dataset #${id} repaired using shapely.make_valid. Repaired geometries: ${res.repaired_count || 0}.`,
    });
    await loadDatasets();
  };

  const handleSeed = async () => {
    setLoading(true);
    const res = await api.seedSampleProject();
    setActionOutput({
      type: "success",
      title: "Baseline Datasets Loaded",
      text: `Standardized Cadastral, Municipal, and Building datasets populated for ${res.region || "Pilot Extent"}.`,
    });
    await loadDatasets();
  };

  return (
    <div className="content">
      <div className="content-wrapper">
        <div className="page-header">
          <div>
            <h1 className="page-title">Data Sources</h1>
            <p className="page-subtitle">
              Manage the spatial datasets used in harmonization, validate topology, and standardize attribute schemas.
            </p>
          </div>

          <div className="header-actions">
            <button className="btn btn-secondary" onClick={handleSeed} disabled={loading}>
              <IconRefresh size={14} />
              Load Baseline Datasets
            </button>
          </div>
        </div>

        {actionOutput && (
          <div
            style={{
              padding: "14px 18px",
              borderRadius: "var(--radius-md)",
              marginBottom: "20px",
              background: actionOutput.type === "success" ? "var(--color-success-bg)" : actionOutput.type === "warning" ? "var(--color-warning-bg)" : "var(--color-danger-bg)",
              color: actionOutput.type === "success" ? "var(--color-success-text)" : actionOutput.type === "warning" ? "var(--color-warning-text)" : "var(--color-danger-text)",
              border: `1px solid ${actionOutput.type === "success" ? "var(--color-success-border)" : actionOutput.type === "warning" ? "var(--color-warning-border)" : "var(--color-danger-border)"}`,
              fontSize: "13px",
            }}
          >
            <div style={{ fontWeight: "700", marginBottom: "4px" }}>
              {actionOutput.title}
            </div>
            <div>{actionOutput.text}</div>
            {actionOutput.details && actionOutput.details.length > 0 && (
              <ul style={{ marginTop: "8px", marginLeft: "20px", fontSize: "12px" }}>
                {actionOutput.details.map((iss, i) => (
                  <li key={i}>
                    Index {iss.feature_index ?? "file"}: {iss.reason} ({iss.code})
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Processing Steps Status Indicator */}
        <div className="panel" style={{ marginBottom: "24px" }}>
          <div className="panel-header">
            <span className="panel-title">Ingestion Lifecycle</span>
          </div>
          <div className="panel-body" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
            {[
              { step: "01", title: "Uploaded", desc: "Dataset registered in database" },
              { step: "02", title: "Validated", desc: "CRS & topology verified" },
              { step: "03", title: "Standardized", desc: "Canonical schema mapping" },
              { step: "04", title: "Ready", desc: "Available for M5 matching" },
            ].map((s, idx) => (
              <div key={idx} style={{ background: "var(--bg-surface-subtle)", padding: "12px 14px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--primary-blue)", fontFamily: "var(--font-mono)", marginBottom: "4px" }}>
                  STAGE {s.step}
                </div>
                <div style={{ fontSize: "13.5px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "2px" }}>
                  {s.title}
                </div>
                <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  {s.desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upload Dropzone Area */}
        <div className="panel" style={{ marginBottom: "24px" }}>
          <div className="panel-header">
            <span className="panel-title">Upload Dataset</span>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Supports GeoJSON, Shapefile (.zip), CSV</span>
          </div>
          <div className="panel-body">
            <form onSubmit={handleUpload} style={{ display: "flex", gap: "16px", alignItems: "flex-end", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: "220px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", marginBottom: "6px", color: "var(--text-secondary)" }}>
                  Dataset Type
                </label>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", background: "white" }}
                >
                  <option value="cadastral">Cadastral Survey (Revenue Department)</option>
                  <option value="municipal">Municipal GIS (Urban Local Body)</option>
                  <option value="building">Building Footprints (Housing Directorate)</option>
                </select>
              </div>

              <div style={{ flex: 2, minWidth: "260px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", marginBottom: "6px", color: "var(--text-secondary)" }}>
                  Geospatial File
                </label>
                <input
                  type="file"
                  accept=".geojson,.json,.zip,.shp"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  style={{ width: "100%", padding: "6px", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", background: "white" }}
                />
              </div>

              <button type="submit" className="btn btn-primary" disabled={!uploadFile || loading}>
                <IconUpload size={14} />
                {loading ? "Uploading..." : "Upload Dataset"}
              </button>
            </form>
          </div>
        </div>

        {/* Registered Datasets Table */}
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Registered Datasets ({datasets.length})</span>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Dataset Name</th>
                  <th>Type</th>
                  <th>Source Authority</th>
                  <th>CRS</th>
                  <th>Features</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <strong>{d.filename}</strong>
                    </td>
                    <td>
                      <span className="badge badge-info">{d.dataset_type?.toUpperCase()}</span>
                    </td>
                    <td>{d.source_name || "Official Registry"}</td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)" }}>{d.crs || "EPSG:4326"}</span>
                    </td>
                    <td>
                      <strong style={{ fontFamily: "var(--font-mono)" }}>{d.feature_count}</strong> features
                    </td>
                    <td>
                      <span className={`badge ${d.status === "standardized" || d.status === "repaired" ? "badge-standardized" : "badge-review"}`}>
                        {d.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleValidate(d.id)}
                          disabled={processingId === d.id}
                        >
                          Validate
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleStandardize(d.id)}
                          disabled={processingId === d.id}
                        >
                          Standardize
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleRepair(d.id)}
                          disabled={processingId === d.id}
                        >
                          Repair
                        </button>
                      </div>
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
