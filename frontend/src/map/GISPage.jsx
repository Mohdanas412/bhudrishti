import React, { useState } from "react";
import MapView from "./MapView";
import LayerControl from "./LayerControl";
import MapLegend from "./MapLegend";
import FeaturePanel from "./FeaturePanel";
import mockMapData from "../mock/map.json";

export default function GISPage() {
  const [layers, setLayers] = useState([
    { id: "parcels", name: "Parcels", visible: true },
    { id: "issues", name: "Issues", visible: true },
    { id: "roads", name: "Roads", visible: false }
  ]);

  const [selectedFeature, setSelectedFeature] = useState(
    mockMapData.features[0] || null
  );

  const toggleLayer = (id) => {
    setLayers((current) =>
      current.map((layer) =>
        layer.id === id
          ? { ...layer, visible: !layer.visible }
          : layer
      )
    );
  };

  const visibleFeatures = mockMapData.features.filter((feature) => {
    if (feature.type === "issue") {
      return layers.find((layer) => layer.id === "issues")?.visible;
    }

    return layers.find((layer) => layer.id === "parcels")?.visible;
  });

  return (
    <section className="gis-page">
      <div className="gis-heading">
        <div>
          <h2>GIS Map</h2>
          <p>View and inspect land parcels and spatial information.</p>
        </div>
      </div>

      <div className="gis-layout">
        <div className="gis-map-wrapper">
          <MapView
            features={visibleFeatures}
            onSelectFeature={setSelectedFeature}
          />
          <LayerControl layers={layers} onToggle={toggleLayer} />
          <MapLegend />
          <FeaturePanel
            feature={selectedFeature}
            onClose={() => setSelectedFeature(null)}
          />
        </div>
      </div>
    </section>
  );
}
