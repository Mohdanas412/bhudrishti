import React from "react";

export default function FeaturePanel({ feature, onClose }) {
  if (!feature) return null;

  return (
    <div className="feature-panel">
      <div className="feature-panel-header">
        <h3>Parcel Details</h3>
        <button onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>

      <div className="feature-details">
        <p>
          <strong>Name:</strong> {feature.name || "N/A"}
        </p>
        <p>
          <strong>ID:</strong> {feature.id || "N/A"}
        </p>
        <p>
          <strong>Status:</strong> {feature.status || "N/A"}
        </p>
        <p>
          <strong>Area:</strong> {feature.area || "N/A"}
        </p>
      </div>
    </div>
  );
}
