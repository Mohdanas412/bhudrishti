import React from "react";

/**
 * FeaturePanel — right-side parcel details drawer in GIS Explorer.
 * Positioned at top:52px, right:12px (via map.css) to clear MapLibre navigation controls.
 */
export default function FeaturePanel({ feature, onClose }) {
  if (!feature) return null;

  const statusColor =
    feature.status === "Verified" ? "var(--color-success-text)" : "var(--color-warning-text)";
  const statusBg =
    feature.status === "Verified" ? "var(--color-success-bg)" : "var(--color-warning-bg)";
  const statusBorder =
    feature.status === "Verified" ? "var(--color-success-border)" : "var(--color-warning-border)";

  return (
    <div className="feature-panel">
      <div className="feature-panel-header">
        <h3>Parcel Details</h3>
        <button onClick={onClose} aria-label="Close parcel details">×</button>
      </div>

      <div className="feature-details">
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          padding: "2px 8px",
          borderRadius: "var(--radius-sm, 4px)",
          fontSize: "11.5px",
          fontWeight: 600,
          background: statusBg,
          color: statusColor,
          border: `1px solid ${statusBorder}`,
          marginBottom: 10,
        }}>
          {feature.status || "Unknown"}
        </div>

        {[
          { label: "Parcel ID", value: feature.id },
          { label: "Owner", value: feature.owner },
          { label: "Land Use", value: feature.land_use },
          { label: "Area", value: feature.area },
          { label: "Type", value: feature.type },
        ].map(({ label, value }) =>
          value ? (
            <p key={label}>
              <strong>{label}:</strong>{" "}
              <span style={{ fontFamily: label === "Parcel ID" || label === "Area" ? "var(--font-mono, monospace)" : "inherit" }}>
                {value}
              </span>
            </p>
          ) : null
        )}
      </div>
    </div>
  );
}
