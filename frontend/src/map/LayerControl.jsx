import React from "react";

export default function LayerControl({ layers, onToggle }) {
  return (
    <div className="map-layer-control">
      <h3>Map Layers</h3>

      {layers.map((layer) => (
        <label className="layer-option" key={layer.id}>
          <input
            type="checkbox"
            checked={layer.visible}
            onChange={() => onToggle(layer.id)}
          />
          <span>{layer.name}</span>
        </label>
      ))}
    </div>
  );
}
