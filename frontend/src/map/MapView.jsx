import React, { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const SATELLITE_STYLE = {
  version: 8,
  sources: {
    "esri-satellite": {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      attribution: "Esri, Maxar, Earthstar Geographics"
    }
  },
  layers: [
    {
      id: "esri-satellite-layer",
      type: "raster",
      source: "esri-satellite",
      minzoom: 0,
      maxzoom: 19
    }
  ]
};

const VECTOR_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

export default function MapView({
  features = [],
  basemap = "vector",
  onSelectFeature,
  selectedFeature
}) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: basemap === "satellite" ? SATELLITE_STYLE : VECTOR_STYLE,
      center: [77.2100, 28.6140],
      zoom: 16,
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

    map.on("load", () => {
      mapRef.current = map;
      updateLayers(map, features, selectedFeature);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Handle basemap changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.setStyle(basemap === "satellite" ? SATELLITE_STYLE : VECTOR_STYLE);
    map.once("style.load", () => {
      updateLayers(map, features, selectedFeature);
    });
  }, [basemap]);

  // Update GeoJSON layers
  const updateLayers = (map, featList, currentSelected) => {
    if (!map || !map.isStyleLoaded()) return;

    const geojson = {
      type: "FeatureCollection",
      features: featList.map((f) => ({
        type: "Feature",
        id: f.id || f.properties?.id,
        properties: f.properties || f,
        geometry: f.geometry || (f.latitude && f.longitude ? {
          type: "Point",
          coordinates: [f.longitude, f.latitude]
        } : null),
      })).filter((f) => f.geometry)
    };

    if (map.getSource("features-source")) {
      map.getSource("features-source").setData(geojson);
    } else {
      map.addSource("features-source", { type: "geojson", data: geojson });

      // Polygon fill
      map.addLayer({
        id: "features-polygon-fill",
        type: "fill",
        source: "features-source",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: {
          "fill-color": [
            "case",
            ["==", ["get", "type"], "cadastral"], "#2563eb",
            ["==", ["get", "type"], "municipal"], "#10b981",
            "#06b6d4"
          ],
          "fill-opacity": 0.3,
        }
      });

      // Polygon stroke
      map.addLayer({
        id: "features-polygon-line",
        type: "line",
        source: "features-source",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: {
          "line-color": [
            "case",
            ["==", ["get", "type"], "cadastral"], "#1d4ed8",
            ["==", ["get", "type"], "municipal"], "#059669",
            "#0891b2"
          ],
          "line-width": 2,
        }
      });

      // Click handler
      map.on("click", "features-polygon-fill", (e) => {
        if (e.features && e.features[0] && onSelectFeature) {
          onSelectFeature(e.features[0].properties);
        }
      });
    }
  };

  useEffect(() => {
    const map = mapRef.current;
    if (map && map.isStyleLoaded()) {
      updateLayers(map, features, selectedFeature);
    }
  }, [features, selectedFeature]);

  return <div ref={containerRef} className="map-container" style={{ width: "100%", height: "100%", minHeight: "550px" }} />;
}
