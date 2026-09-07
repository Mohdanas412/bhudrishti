import React, { useState } from "react";
import { Link } from "react-router-dom";
import BhuDrishtiLogo from "../components/BhuDrishtiLogo";
import {
  IconWorkspace,
  IconDashboard,
  IconDataSources,
  IconCheckCircle,
  IconShield,
  IconAlertCircle,
  IconArrowRight,
  IconCheck
} from "../components/Icons";

export default function LandingPage() {
  const [reconcileState, setReconcileState] = useState("after"); // 'before' | 'after'

  return (
    <div className="landing-page">
      {/* Light Navigation Header */}
      <header className="landing-nav">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <BhuDrishtiLogo size={34} showText={true} subtitle="Land Data Intelligence" />
        </div>

        <nav className="landing-nav-links">
          <a href="#problem">The Problem</a>
          <a href="#pipeline">How It Works</a>
          <a href="#sources">Multi-Source Data</a>
          <a href="#reconciliation">Intelligent Reconcile</a>
          <a href="#traceability">Trust & Traceability</a>
        </nav>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Link to="/dashboard" className="btn btn-secondary btn-sm">
            Command Center
          </Link>
          <Link to="/workspace" className="btn btn-primary btn-sm">
            Open Workspace <IconArrowRight size={14} />
          </Link>
        </div>
      </header>

      {/* Hero Section — Light Theme, Spacious Typography */}
      <section className="landing-hero">
        <div className="hero-badge">
          <IconShield size={14} color="var(--primary-blue)" />
          <span>Automated Integration & Intelligent Harmonization of Geospatial Land Records</span>
        </div>

        <h1 className="hero-title">
          Harmonize the map.<br />
          <span>Resolve the record.</span>
        </h1>

        <p className="hero-subtitle">
          Bring fragmented cadastral surveys, municipal GIS boundaries, and building footprints into one trusted, mathematically reconciled spatial registry.
        </p>

        <div className="hero-cta-group">
          <Link to="/workspace" className="btn btn-primary btn-lg">
            <IconWorkspace size={18} />
            Open Harmonization Workspace
          </Link>
          <a href="#pipeline" className="btn btn-secondary btn-lg">
            See How It Works
          </a>
        </div>

        {/* Clean Geospatial Visual Graphic */}
        <div style={{ marginTop: "48px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-xl)", padding: "24px", boxShadow: "var(--shadow-lg)", overflow: "hidden" }}>
          <svg width="100%" height="280" viewBox="0 0 800 280" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="800" height="280" fill="#f8fafc" rx="8" />
            <path d="M 0 70 H 800 M 0 140 H 800 M 0 210 H 800 M 200 0 V 280 M 400 0 V 280 M 600 0 V 280" stroke="#e2e8f0" strokeWidth="1" />

            {/* Cadastral Polygon (Blue) */}
            <polygon points="180,50 360,40 390,200 200,210" fill="rgba(37, 99, 235, 0.12)" stroke="#2563eb" strokeWidth="2.5" />
            <text x="210" y="80" fill="#1e40af" fontSize="12" fontWeight="700" fontFamily="sans-serif">Cadastral Survey (P-102): 1,240 m²</text>

            {/* Municipal Polygon (Green - Offset) */}
            <polygon points="175,45 368,38 398,205 195,215" fill="rgba(22, 163, 74, 0.1)" stroke="#16a34a" strokeWidth="2" strokeDasharray="4 2" />
            <text x="230" y="180" fill="#15803d" fontSize="12" fontWeight="700" fontFamily="sans-serif">Municipal GIS (M-458): 1,256 m²</text>

            {/* Variance Highlight */}
            <circle cx="394" cy="202" r="14" fill="rgba(220, 38, 38, 0.15)" stroke="#dc2626" strokeWidth="1.5" />
            <text x="420" y="206" fill="#b91c1c" fontSize="12" fontWeight="bold" fontFamily="sans-serif">Δ 16 m² Area Variance</text>
          </svg>
        </div>
      </section>

      {/* Section 1: The Problem */}
      <section id="problem" className="landing-section" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <span className="section-tag">Urban Land Challenge</span>
        <h2 className="section-heading">Land data rarely tells one consistent story.</h2>
        <p className="section-desc">
          State Revenue Departments, Municipal Urban Local Bodies, and Building Registries describe the same physical ground with different geometries, discordant areas, and disjointed attributes.
        </p>

        {/* Visual Workflow Diagram: Source A + B + C -> Discrepancies -> BhuDrishti -> Harmonized */}
        <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-xl)", padding: "32px", boxShadow: "var(--shadow-sm)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", alignItems: "center" }}>
            <div style={{ background: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--primary-blue)", textTransform: "uppercase", marginBottom: "4px" }}>Source A</div>
              <div style={{ fontSize: "14px", fontWeight: "700", marginBottom: "4px" }}>Cadastral Survey</div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>1,240 m² • Owner: Ramesh Sharma</div>
            </div>

            <div style={{ background: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--color-success)", textTransform: "uppercase", marginBottom: "4px" }}>Source B</div>
              <div style={{ fontSize: "14px", fontWeight: "700", marginBottom: "4px" }}>Municipal Property GIS</div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>1,256 m² • Zone R-2 Dwarka</div>
            </div>

            <div style={{ background: "var(--bg-surface-subtle)", padding: "16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--color-warning)", textTransform: "uppercase", marginBottom: "4px" }}>Source C</div>
              <div style={{ fontSize: "14px", fontWeight: "700", marginBottom: "4px" }}>Building Footprint</div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Residential Villa (Built-up)</div>
            </div>
          </div>

          <div style={{ textAlign: "center", margin: "24px 0 16px" }}>
            <span className="badge badge-danger" style={{ padding: "6px 16px", fontSize: "12px" }}>
              <IconAlertCircle size={14} /> Discrepancies: Δ 16 m² Area Delta & Slivers Detected
            </span>
          </div>

          <div style={{ background: "var(--primary-blue-subtle)", border: "1px solid var(--primary-blue-border)", borderRadius: "var(--radius-lg)", padding: "20px", textAlign: "center" }}>
            <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary-blue)", textTransform: "uppercase", marginBottom: "4px" }}>
              BhuDrishti Integration & Reconciliation Core
            </div>
            <div style={{ fontSize: "15px", fontWeight: "700", color: "var(--text-primary)" }}>
              Reconciles Geometry Baseline (Cadastral 0.95) & Merges Validated Municipal Attributes
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: How It Works — Pipeline */}
      <section id="pipeline" className="landing-section" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <span className="section-tag">Deterministic Workflow</span>
        <h2 className="section-heading">How BhuDrishti Works</h2>
        <p className="section-desc">
          A disciplined 7-stage spatial data pipeline combining mathematical scoring with transparent human-in-the-loop verification.
        </p>

        <div className="pipeline-track">
          {[
            { step: "01", title: "Upload", desc: "GeoJSON, SHP & CSV Ingest" },
            { step: "02", title: "Validate", desc: "CRS & Topology Checks" },
            { step: "03", title: "Standardize", desc: "Canonical Schema Alignment" },
            { step: "04", title: "Match", desc: "IoU & Centroid Proximity" },
            { step: "05", title: "Detect", desc: "Area & Boundary Discrepancies" },
            { step: "06", title: "Review", desc: "Officer Audit & Oversight" },
            { step: "07", title: "Harmonize", desc: "Unified Certified Map Record" },
          ].map((item, idx) => (
            <div key={idx} className="pipeline-card">
              <div className="pipeline-step-num">{item.step}</div>
              <div className="pipeline-step-title">{item.title}</div>
              <div className="pipeline-step-sub">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Section 3: Multi-Source Data Layers */}
      <section id="sources" className="landing-section" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <span className="section-tag">Institutional Sources</span>
        <h2 className="section-heading">Multi-Source Spatial Ingestion</h2>
        <p className="section-desc">
          Harmonizing institutional layers into a standardized EPSG:4326 geometry representation.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "20px" }}>
          <div className="panel" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span className="badge badge-info">Cadastral Survey</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>Weight: 0.95</span>
            </div>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "8px" }}>State Land Revenue</h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              Legal boundary ground measurements, plot numbers, deeded ownership titles, and revenue classifications.
            </p>
          </div>

          <div className="panel" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span className="badge badge-verified">Municipal GIS</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>Weight: 0.82</span>
            </div>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "8px" }}>Urban Local Body</h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              Property tax assessment IDs, street addresses, postal codes, utility connections, and ward zoning rules.
            </p>
          </div>

          <div className="panel" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span className="badge badge-warning">Building Footprints</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>Weight: 0.88</span>
            </div>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "8px" }}>Housing Registry</h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              High-resolution structural outlines, built-up ground coverage, construction status, and occupancy metadata.
            </p>
          </div>

          <div className="panel" style={{ padding: "24px", borderStyle: "dashed" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span className="badge badge-info" style={{ background: "var(--bg-surface-subtle)", color: "var(--text-secondary)", borderColor: "var(--border-subtle)" }}>Extensibility</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Architecture Ready</span>
            </div>
            <h3 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "8px", color: "var(--text-secondary)" }}>Satellite & GNSS Sensor</h3>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.5" }}>
              Future extensible ingestion pipeline for drone orthomosaics, satellite imagery, and high-accuracy GNSS field surveys.
            </p>
          </div>
        </div>
      </section>

      {/* Section 4: Intelligent Reconciliation Before vs After */}
      <section id="reconciliation" className="landing-section" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <span className="section-tag">Visual Verification</span>
        <h2 className="section-heading">Before vs After Harmonization</h2>
        <p className="section-desc">
          Compare how overlapping, divergent source polygons are mathematically reconciled into a single certified spatial boundary.
        </p>

        <div className="panel" style={{ padding: "32px" }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "24px" }}>
            <div className="filter-chip-group" style={{ background: "var(--bg-surface-subtle)", padding: "4px", borderRadius: "var(--radius-md)" }}>
              <button
                className={`filter-chip ${reconcileState === "before" ? "active" : ""}`}
                onClick={() => setReconcileState("before")}
                style={{ padding: "8px 18px" }}
              >
                Before: Multi-Source Divergence
              </button>
              <button
                className={`filter-chip ${reconcileState === "after" ? "active" : ""}`}
                onClick={() => setReconcileState("after")}
                style={{ padding: "8px 18px" }}
              >
                After: Certified Harmonized Result
              </button>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "32px", alignItems: "center" }}>
            <div style={{ background: "#f8fafc", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-lg)", height: "260px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="100%" height="100%" viewBox="0 0 400 240" fill="none">
                <path d="M 0 60 H 400 M 0 120 H 400 M 0 180 H 400 M 100 0 V 240 M 200 0 V 240 M 300 0 V 240" stroke="#e2e8f0" strokeWidth="1" />

                {reconcileState === "before" ? (
                  <>
                    <polygon points="100,50 260,40 280,170 120,180" fill="rgba(37, 99, 235, 0.18)" stroke="#2563eb" strokeWidth="2.5" />
                    <text x="120" y="75" fill="#1e40af" fontSize="11" fontWeight="700" fontFamily="sans-serif">Cadastral: 1,240 m²</text>

                    <polygon points="95,45 265,38 290,175 115,185" fill="rgba(22, 163, 74, 0.15)" stroke="#16a34a" strokeWidth="2" strokeDasharray="4 2" />
                    <text x="140" y="160" fill="#15803d" fontSize="11" fontWeight="700" fontFamily="sans-serif">Municipal: 1,256 m²</text>
                  </>
                ) : (
                  <>
                    <polygon points="100,50 260,40 280,170 120,180" fill="rgba(124, 58, 237, 0.2)" stroke="#7c3aed" strokeWidth="3" />
                    <text x="130" y="110" fill="#6d28d9" fontSize="13" fontWeight="bold" fontFamily="sans-serif">HARM-P-102</text>
                    <text x="125" y="130" fill="#4c1d95" fontSize="11" fontFamily="sans-serif">Certified Area: 1,240 m²</text>
                    <text x="125" y="148" fill="#15803d" fontSize="10.5" fontWeight="600" fontFamily="sans-serif">✓ Attributes Merged</text>
                  </>
                )}
              </svg>
            </div>

            <div>
              <h3 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "10px" }}>
                {reconcileState === "before"
                  ? "Divergent Multi-Source Polygons"
                  : "Certified Single-Source-of-Truth"}
              </h3>

              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: "1.6", marginBottom: "16px" }}>
                {reconcileState === "before"
                  ? "Cadastral Survey and Municipal property GIS disagreed on boundary lines, producing an unresolvable 16 m² area delta and isolated title records."
                  : "BhuDrishti's M5 reconciliation engine resolved the conflict: cadastral geometry was preserved as the legal ground baseline (reliability 0.95), while MCD tax zones, addresses, and occupancy status were merged into a certified record."}
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <IconCheckCircle size={16} color="var(--color-success)" />
                  <span>Geometry Similarity (IoU): <strong>86%</strong></span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <IconCheckCircle size={16} color="var(--color-success)" />
                  <span>Recommendation: <strong>Prefer Cadastral Baseline & Merge Attributes</strong></span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <IconCheckCircle size={16} color="var(--color-success)" />
                  <span>Audit Trail: <strong>Recorded with Officer Sign-off</strong></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 5: Trust & Traceability */}
      <section id="traceability" className="landing-section" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <span className="section-tag">Governance & Compliance</span>
        <h2 className="section-heading">Built for Institutional Trust</h2>
        <p className="section-desc">
          Every harmonized parcel retains complete provenance, capturing confidence scores, evidence ratios, and officer review timestamps.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
          <div className="panel" style={{ padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>Scoring Basis</div>
            <h4 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "6px" }}>Multimodal Evidence</h4>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>Transparent scoring across IoU overlap, centroid proximity, and area proportions.</p>
          </div>

          <div className="panel" style={{ padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>Canonical Rules</div>
            <h4 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "6px" }}>Explainable Actions</h4>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>Explicit recommendation logic based on institutional reliability weights.</p>
          </div>

          <div className="panel" style={{ padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>Human Oversight</div>
            <h4 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "6px" }}>Officer Sign-Off</h4>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>Officer review queue for any discrepancies exceeding tolerance thresholds.</p>
          </div>

          <div className="panel" style={{ padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "4px" }}>Standard Output</div>
            <h4 style={{ fontSize: "15px", fontWeight: "700", marginBottom: "6px" }}>Certified GeoJSON</h4>
            <p style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>Production-ready GeoJSON and CSV exports for state GIS portals.</p>
          </div>
        </div>
      </section>

      {/* Final Call to Action */}
      <section className="landing-section" style={{ textAlign: "center", paddingBottom: "100px" }}>
        <div style={{ background: "var(--primary-blue-subtle)", border: "1px solid var(--primary-blue-border)", borderRadius: "var(--radius-xl)", padding: "48px 32px" }}>
          <h2 style={{ fontSize: "32px", fontWeight: "800", color: "var(--text-primary)", marginBottom: "12px" }}>
            From fragmented land data to one trusted spatial view.
          </h2>
          <p style={{ fontSize: "15.5px", color: "var(--text-secondary)", maxWidth: "560px", margin: "0 auto 28px" }}>
            Launch the interactive BhuDrishti workstation to inspect candidate matches, resolve discrepancies, and export harmonized land parcels.
          </p>
          <Link to="/workspace" className="btn btn-primary btn-lg">
            Open BhuDrishti Workspace <IconArrowRight size={16} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid var(--border-subtle)", padding: "32px 40px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px", fontSize: "12px", color: "var(--text-secondary)", background: "white" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <BhuDrishtiLogo size={24} showText={true} subtitle="" />
          <span>• Urban Land Data Harmonization Platform</span>
        </div>
        <div>
          <span>EPSG:4326 Compliant • Automated Spatial Reconciliation Engine</span>
        </div>
      </footer>
    </div>
  );
}
