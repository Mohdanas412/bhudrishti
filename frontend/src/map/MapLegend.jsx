import React from "react";

export default function MapLegend() {
  return (
    <div className="map-legend">
      <h3>Legend</h3>

      <div className="legend-item">
        <span className="legend-dot verified"></span>
        Verified
      </div>

      <div className="legend-item">
        <span className="legend-dot review"></span>
        Under Review
      </div>

      <div className="legend-item">
        <span className="legend-dot issue"></span>
        Issue Detected
      </div>
    </div>
  );
}
