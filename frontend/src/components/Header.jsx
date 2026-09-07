import React, { useEffect, useState } from "react";
import { api, dataMode } from "../services/api";
import { IconRefresh, IconCrosshair } from "./Icons";

/**
 * Header — top application bar.
 *
 * Shows a truthful Data Mode badge:
 *   Connecting...  — initial health check in progress
 *   Backend Connected — FastAPI at API_BASE is responding
 *   Demo Mode — backend unreachable; synthetic fixtures are in use
 *
 * Removed: fake "Directorate of Land Records" organization label.
 */
export default function Header() {
  const [connectionState, setConnectionState] = useState("connecting"); // "connecting" | "live" | "demo"
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    async function ping() {
      const res = await api.checkHealth();
      setConnectionState(res.online ? "live" : "demo");
    }
    ping();
    const interval = setInterval(ping, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleQuickSeed = async () => {
    setSeeding(true);
    try {
      await api.seedSampleProject();
    } finally {
      setSeeding(false);
      window.location.reload();
    }
  };

  const modeBadgeStyle = {
    display: "flex",
    alignItems: "center",
    gap: 6,
    fontSize: "11.5px",
    fontWeight: 500,
    padding: "3px 10px",
    borderRadius: "var(--radius-full)",
    border: "1px solid transparent",
    ...(connectionState === "live"
      ? { background: "var(--color-success-bg)", color: "var(--color-success-text)", borderColor: "var(--color-success-border)" }
      : connectionState === "demo"
      ? { background: "var(--color-warning-bg)", color: "var(--color-warning-text)", borderColor: "var(--color-warning-border)" }
      : { background: "var(--bg-surface-subtle)", color: "var(--text-muted)", borderColor: "var(--border-subtle)" })
  };

  const dotColor =
    connectionState === "live" ? "var(--color-success)"
    : connectionState === "demo" ? "var(--color-warning)"
    : "var(--text-muted)";

  const modeLabel =
    connectionState === "live" ? "Backend Connected"
    : connectionState === "demo" ? "Demo Mode"
    : "Connecting...";

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-region-badge">
          <IconCrosshair size={14} color="var(--primary-blue)" />
          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Extent:</span>
          <span>Dwarka Sector 14, New Delhi · EPSG:4326</span>
        </div>
      </div>

      <div className="header-right">
        <button
          className="btn btn-secondary btn-sm"
          onClick={handleQuickSeed}
          disabled={seeding}
          title="Seed and standardize sample Cadastral, Municipal, and Building datasets for testing"
        >
          <IconRefresh size={13} />
          {seeding ? "Seeding..." : "Load Sample Datasets"}
        </button>

        <div style={modeBadgeStyle}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", display: "inline-block", background: dotColor }} />
          <span>{modeLabel}</span>
        </div>

        {connectionState === "demo" && (
          <div
            title="Backend is unavailable. The application is showing synthetic test data to demonstrate the harmonization workflow."
            style={{ fontSize: "10.5px", color: "var(--text-muted)", fontStyle: "italic" }}
          >
            Synthetic data active
          </div>
        )}
      </div>
    </header>
  );
}
