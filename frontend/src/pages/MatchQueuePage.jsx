import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import {
  IconWorkspace,
  IconSearch,
  IconArrowRight
} from "../components/Icons";

export default function MatchQueuePage() {
  const [matches, setMatches] = useState([]);
  const [scoreFilter, setScoreFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const data = await api.getMatches();
      setMatches(data);
      setLoading(false);
    }
    load();
  }, []);

  const filteredMatches = matches.filter((m) => {
    if (scoreFilter === "high" && m.score < 90) return false;
    if (scoreFilter === "review" && (m.score < 70 || m.score >= 90)) return false;
    if (scoreFilter === "low" && m.score >= 70) return false;

    if (search) {
      const q = search.toLowerCase();
      const a = m.feature_a.toLowerCase().includes(q);
      const b = m.feature_b.toLowerCase().includes(q);
      const owner = (m.feature_a_details?.owner || "").toLowerCase().includes(q);
      if (!a && !b && !owner) return false;
    }
    return true;
  });

  return (
    <div className="content">
      <div className="content-wrapper">
        <div className="page-header">
          <div>
            <h1 className="page-title">Candidate Match Review</h1>
            <p className="page-subtitle">
              Pairwise candidate matches generated via IoU geometry overlap, centroid proximity, and source reliability weights.
            </p>
          </div>

          <div className="header-actions">
            <Link to="/workspace" className="btn btn-primary">
              <IconWorkspace size={15} />
              Open Workspace
            </Link>
          </div>
        </div>

        <div className="panel" style={{ marginBottom: "20px" }}>
          <div className="panel-body" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
            <div className="filter-chip-group">
              <button className={`filter-chip ${scoreFilter === "all" ? "active" : ""}`} onClick={() => setScoreFilter("all")}>
                All Pairs ({matches.length})
              </button>
              <button className={`filter-chip ${scoreFilter === "high" ? "active" : ""}`} onClick={() => setScoreFilter("high")}>
                High Confidence (&ge;90%)
              </button>
              <button className={`filter-chip ${scoreFilter === "review" ? "active" : ""}`} onClick={() => setScoreFilter("review")}>
                Review Band (70–89%)
              </button>
              <button className={`filter-chip ${scoreFilter === "low" ? "active" : ""}`} onClick={() => setScoreFilter("low")}>
                Low Agreement (&lt;70%)
              </button>
            </div>

            <div style={{ minWidth: "240px", position: "relative" }}>
              <input
                type="text"
                placeholder="Search Parcel ID or Owner..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ width: "100%", padding: "6px 10px 6px 28px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", fontSize: "12px" }}
              />
              <span style={{ position: "absolute", left: "8px", top: "7px", color: "var(--text-muted)" }}>
                <IconSearch size={14} />
              </span>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Cadastral Feature (A)</th>
                  <th>Municipal Feature (B)</th>
                  <th>Owner / Address</th>
                  <th>Confidence</th>
                  <th>Geometry IoU</th>
                  <th>Proximity</th>
                  <th>Area Similarity</th>
                  <th>Land Use</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredMatches.map((m) => (
                  <tr key={m.feature_a}>
                    <td><strong>{m.feature_a}</strong></td>
                    <td>{m.feature_b}</td>
                    <td>
                      <div style={{ fontSize: "12px" }}>
                        <div>{m.feature_a_details?.owner || "—"}</div>
                        <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>{m.feature_b_details?.address || "—"}</div>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: "700", color: m.score >= 90 ? "var(--color-success)" : "var(--color-warning)" }}>
                        {m.score}%
                      </span>
                    </td>
                    <td>{Math.round((m.breakdown?.components?.geometry || 0.86) * 100)}%</td>
                    <td>{Math.round((m.breakdown?.components?.proximity || 0.94) * 100)}%</td>
                    <td>{Math.round((m.breakdown?.components?.area || 0.90) * 100)}%</td>
                    <td>{m.feature_a_details?.land_use || "Residential"}</td>
                    <td>
                      <span className={`badge ${m.status === "matched" ? "badge-matched" : "badge-review"}`}>
                        {m.status === "matched" ? "Auto-Matched" : "Review Required"}
                      </span>
                    </td>
                    <td>
                      <Link
                        to="/workspace"
                        state={{ focusFeature: m.feature_a }}
                        className="btn btn-secondary btn-sm"
                      >
                        Investigate <IconArrowRight size={12} />
                      </Link>
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
