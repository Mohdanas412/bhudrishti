import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import {
  IconWorkspace,
  IconCheck,
  IconArrowRight
} from "../components/Icons";

export default function ConflictReviewPage() {
  const [conflicts, setConflicts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [typeFilter, setTypeFilter] = useState("all");
  const [actionAlert, setActionAlert] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    const [c, r] = await Promise.all([
      api.getConflicts(),
      api.getRecommendations(),
    ]);
    setConflicts(c);
    setRecommendations(r);
    setLoading(false);
  };

  const handleResolve = async (conflictId, decision) => {
    await api.submitReview(conflictId, {
      decision,
      reviewer: "Cadastral Officer",
      comment: `Reconciled via ${decision.toUpperCase()} decision.`,
    });

    setActionAlert({
      type: "success",
      text: `Conflict #${conflictId} recorded as "${decision.toUpperCase()}". Harmonized registry updated.`,
    });

    setConflicts((prev) =>
      prev.map((c) => (c.id === conflictId ? { ...c, status: "resolved" } : c))
    );
  };

  const filteredConflicts = conflicts.filter((c) => {
    if (typeFilter !== "all" && c.type !== typeFilter) return false;
    return true;
  });

  const unresolvedCount = conflicts.filter((c) => c.status !== "resolved").length;
  const highCount = conflicts.filter((c) => c.severity === "high").length;
  const resolvedCount = conflicts.filter((c) => c.status === "resolved").length;

  return (
    <div className="content">
      <div className="content-wrapper">
        <div className="page-header">
          <div>
            <h1 className="page-title">Conflicts Triage</h1>
            <p className="page-subtitle">
              Formal discrepancy queue for cross-dataset spatial boundary shifts, area variances, and attribute mismatches.
            </p>
          </div>

          <div className="header-actions">
            <Link to="/workspace" className="btn btn-primary">
              <IconWorkspace size={15} />
              Open Workspace
            </Link>
          </div>
        </div>

        {/* Top Summary Row per Section 30 */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "20px" }}>
          <div className="metric-box-compact">
            <div className="metric-box-title">Unresolved Conflicts</div>
            <div className="metric-box-value" style={{ color: unresolvedCount > 0 ? "var(--color-danger)" : "var(--color-success)" }}>
              {unresolvedCount}
            </div>
          </div>
          <div className="metric-box-compact">
            <div className="metric-box-title">High Priority</div>
            <div className="metric-box-value" style={{ color: "var(--color-danger)" }}>
              {highCount}
            </div>
          </div>
          <div className="metric-box-compact">
            <div className="metric-box-title">Resolved & Certified</div>
            <div className="metric-box-value" style={{ color: "var(--color-success)" }}>
              {resolvedCount}
            </div>
          </div>
        </div>

        {actionAlert && (
          <div
            style={{
              padding: "12px 16px",
              borderRadius: "var(--radius-md)",
              background: "var(--color-success-bg)",
              color: "var(--color-success-text)",
              border: "1px solid var(--color-success-border)",
              marginBottom: "20px",
              fontSize: "13px",
              fontWeight: "500",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <IconCheck size={16} />
            <span>{actionAlert.text}</span>
          </div>
        )}

        {/* Filter Toolbar */}
        <div className="panel" style={{ marginBottom: "20px" }}>
          <div className="panel-body" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div className="filter-chip-group">
              <button className={`filter-chip ${typeFilter === "all" ? "active" : ""}`} onClick={() => setTypeFilter("all")}>
                All Discrepancies ({conflicts.length})
              </button>
              <button className={`filter-chip ${typeFilter === "area" ? "active" : ""}`} onClick={() => setTypeFilter("area")}>
                Area Discrepancies ({conflicts.filter((c) => c.type === "area").length})
              </button>
              <button className={`filter-chip ${typeFilter === "geometry" ? "active" : ""}`} onClick={() => setTypeFilter("geometry")}>
                Geometry Mismatches ({conflicts.filter((c) => c.type === "geometry").length})
              </button>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Showing {filteredConflicts.length} item(s)
            </div>
          </div>
        </div>

        {/* Conflicts List Cards */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {filteredConflicts.map((c) => {
            const rec = recommendations.find((r) => r.conflict_id === c.id);
            const isResolved = c.status === "resolved";

            return (
              <div key={c.id} className="panel" style={{ borderLeft: `4px solid ${isResolved ? "var(--color-success)" : "var(--color-danger)"}` }}>
                <div className="panel-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span className={`badge ${isResolved ? "badge-resolved" : "badge-conflict"}`}>
                      #C-{c.id} • {c.type?.toUpperCase()}
                    </span>
                    <span style={{ fontWeight: "700", fontSize: "14px" }}>
                      Source A: Cadastral {c.feature_a} ↔ Source B: Municipal {c.feature_b}
                    </span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className={`badge ${c.severity === "high" ? "badge-danger" : "badge-warning"}`}>
                      {c.severity} priority
                    </span>
                    <span className={`badge ${isResolved ? "badge-resolved" : "badge-review"}`}>
                      {isResolved ? "Resolved" : "Pending Review"}
                    </span>
                  </div>
                </div>

                <div className="panel-body">
                  <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1.2fr", gap: "24px" }}>
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-secondary)", textTransform: "uppercase", marginBottom: "6px" }}>
                        Evidence Breakdown
                      </div>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "14px", lineHeight: "1.5" }}>
                        {c.reason}
                      </p>

                        <div style={{ display: "flex", gap: "16px", background: "var(--bg-surface-subtle)", padding: "12px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
                          <div>
                            <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block" }}>Source A</span>
                            <strong style={{ fontSize: "13px" }}>{c.feature_a_details?.area || "1,240"} m²</strong>
                          </div>
                          <div style={{ borderLeft: "1px solid var(--border-subtle)", paddingLeft: "16px" }}>
                            <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "block" }}>Source B</span>
                            <strong style={{ fontSize: "13px" }}>{c.feature_b_details?.area || "1,256"} m²</strong>
                          </div>
                          <div style={{ borderLeft: "1px solid var(--border-subtle)", paddingLeft: "16px" }}>
                            <span style={{ fontSize: "11px", color: "var(--color-danger)", fontWeight: "600", display: "block" }}>Variance</span>
                            <strong style={{ fontSize: "13px", color: "var(--color-danger)" }}>Δ {c.area_difference ? c.area_difference.toFixed(1) : "16.0"} m²</strong>
                          </div>
                        </div>
                    </div>

                    <div style={{ background: "var(--color-info-bg)", border: "1px solid var(--color-info-border)", borderRadius: "var(--radius-md)", padding: "14px" }}>
                      <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--color-info-text)", textTransform: "uppercase", marginBottom: "4px" }}>
                        AI Recommendation (Confidence: {rec?.confidence || 89}%)
                      </div>
                      <div style={{ fontWeight: "700", color: "#0369a1", fontSize: "13px", marginBottom: "6px" }}>
                        {rec?.action === "prefer_source" ? "Action: Prefer Cadastral Baseline" : "Action: Merge Attributes"}
                      </div>
                      <p style={{ fontSize: "12px", color: "#0c4a6e", marginBottom: "14px", lineHeight: "1.4" }}>
                        {rec?.reason || "Cadastral survey baseline holds legal precedence over municipal tax boundaries."}
                      </p>

                      {!isResolved ? (
                        <div style={{ display: "flex", gap: "8px" }}>
                          <button
                            className="btn btn-success btn-sm"
                            onClick={() => handleResolve(c.id, "accept")}
                          >
                            Accept
                          </button>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleResolve(c.id, "reject")}
                          >
                            Reject
                          </button>
                          <Link
                            to="/workspace"
                            state={{ focusFeature: c.feature_a }}
                            className="btn btn-secondary btn-sm"
                          >
                            Inspect on Map <IconArrowRight size={12} />
                          </Link>
                        </div>
                      ) : (
                        <div style={{ fontSize: "12px", color: "var(--color-success)", fontWeight: "600", display: "flex", alignItems: "center", gap: "6px" }}>
                          <IconCheck size={14} />
                          <span>Certified by Reviewing Officer</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
