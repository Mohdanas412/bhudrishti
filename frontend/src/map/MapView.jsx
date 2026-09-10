import React, { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import DynamicGisCanvas from "./DynamicGisCanvas";

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

const VECTOR_STYLE = {
  version: 8,
  sources: {
    "carto-positron": {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors, © CARTO"
    }
  },
  layers: [
    {
      id: "carto-positron-layer",
      type: "raster",
      source: "carto-positron",
      minzoom: 0,
      maxzoom: 20
    }
  ]
};

const DARK_STYLE = {
  version: 8,
  sources: {
    "carto-dark": {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors, © CARTO"
    }
  },
  layers: [
    {
      id: "carto-dark-layer",
      type: "raster",
      source: "carto-dark",
      minzoom: 0,
      maxzoom: 20
    }
  ]
};

const getBasemapStyle = (mode) => {
  if (mode === "satellite") return SATELLITE_STYLE;
  if (mode === "dark") return DARK_STYLE;
  return VECTOR_STYLE;
};

export default function MapView({
  features = [],
  basemap = "vector",
  onSelectFeature,
  selectedFeature
}) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  const [mapSupported, setMapSupported] = useState(true);
  const [cursorCoords, setCursorCoords] = useState(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    try {
      if (!maplibregl.supported()) {
        setMapSupported(false);
        return;
      }

      const map = new maplibregl.Map({
        container: containerRef.current,
        style: getBasemapStyle(basemap),
        center: [77.2100, 28.6140],
        zoom: 16,
      });

      map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

      map.on("load", () => {
        mapRef.current = map;
        updateLayers(map, features, selectedFeature, basemap);
      });

      map.on("mousemove", (e) => {
        setCursorCoords({
          lon: e.lngLat.lng,
          lat: e.lngLat.lat,
          zoom: map.getZoom().toFixed(1),
        });
      });

      map.on("mouseout", () => {
        setCursorCoords(null);
      });

      return () => {
        try {
          map.remove();
        } catch {
          // ignore cleanup errors
        }
        mapRef.current = null;
      };
    } catch (err) {
      console.warn("MapView WebGL note:", err.message);
      setMapSupported(false);
    }
  }, []);

  // Handle basemap changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    map.setStyle(getBasemapStyle(basemap));

    const onStyleData = () => {
      if (map.isStyleLoaded()) {
        map.off("styledata", onStyleData);
        updateLayers(map, features, selectedFeature, basemap);
      }
    };
    map.on("styledata", onStyleData);
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

      // Polygon / MultiPolygon fill
      map.addLayer({
        id: "features-polygon-fill",
        type: "fill",
        source: "features-source",
        filter: ["match", ["geometry-type"], ["Polygon", "MultiPolygon"], true, false],
        paint: {
          "fill-color": [
            "case",
            ["==", ["get", "type"], "cadastral"], "#2563eb",
            ["==", ["get", "type"], "municipal"], "#10b981",
            ["==", ["get", "type"], "building"], "#8b5cf6",
            ["==", ["get", "type"], "harmonized"], "#059669",
            ["==", ["get", "type"], "encroachment"], "#ef4444",
            ["==", ["get", "type"], "conflict"], "#f59e0b",
            ["==", ["get", "dataset_type"], "cadastral"], "#2563eb",
            ["==", ["get", "dataset_type"], "municipal"], "#10b981",
            ["==", ["get", "dataset_type"], "building"], "#8b5cf6",
            "#06b6d4"
          ],
          "fill-opacity": 0.35,
        }
      });

      // Polygon / MultiPolygon stroke
      map.addLayer({
        id: "features-polygon-line",
        type: "line",
        source: "features-source",
        filter: ["match", ["geometry-type"], ["Polygon", "MultiPolygon"], true, false],
        paint: {
          "line-color": [
            "case",
            ["==", ["get", "type"], "cadastral"], "#1d4ed8",
            ["==", ["get", "type"], "municipal"], "#047857",
            ["==", ["get", "type"], "building"], "#7c3aed",
            ["==", ["get", "type"], "harmonized"], "#047857",
            ["==", ["get", "type"], "encroachment"], "#dc2626",
            ["==", ["get", "type"], "conflict"], "#d97706",
            ["==", ["get", "dataset_type"], "cadastral"], "#1d4ed8",
            ["==", ["get", "dataset_type"], "municipal"], "#047857",
            ["==", ["get", "dataset_type"], "building"], "#7c3aed",
            "#0891b2"
          ],
          "line-width": 2,
        }
      });

      // Point / Discrepancy hotspot marker circles
      map.addLayer({
        id: "features-points",
        type: "circle",
        source: "features-source",
        filter: ["==", ["geometry-type"], "Point"],
        paint: {
          "circle-radius": 6,
          "circle-color": [
            "case",
            ["==", ["get", "severity"], "high"], "#ef4444",
            ["==", ["get", "severity"], "medium"], "#f59e0b",
            "#2563eb"
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#ffffff",
        }
      });

      // Click handler
      map.on("click", "features-polygon-fill", (e) => {
        if (e.features && e.features[0] && onSelectFeature) {
          onSelectFeature(e.features[0].properties);
        }
      });

      map.on("click", "features-points", (e) => {
        if (e.features && e.features[0] && onSelectFeature) {
          onSelectFeature(e.features[0].properties);
        }
      });
    }
  };

  useEffect(() => {
    const map = mapRef.current;
    if (map && map.isStyleLoaded()) {
      updateLayers(map, features, selectedFeature, basemap);
    }
  }, [features, selectedFeature, basemap]);

  if (!mapSupported) {
    const cadastralFeats = features.filter((f) => f.type === "cadastral" || f.id?.startsWith("P-") || f.id?.startsWith("PB-"));
    const municipalFeats = features.filter((f) => f.type === "municipal" || f.id?.startsWith("M-") || f.id?.startsWith("PCH-"));

    const syntheticMatch = {
      feature_a: selectedFeature?.id || cadastralFeats[0]?.id || "P-101",
      feature_b: municipalFeats[0]?.id || "M-456",
      score: 95,
      feature_a_details: selectedFeature || cadastralFeats[0] || {
        id: "P-101",
        area: 1050,
        geometry: {
          type: "Polygon",
          coordinates: [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]
        }
      },
      feature_b_details: municipalFeats[0] || {
        id: "M-456",
        area: 1050,
        geometry: {
          type: "Polygon",
          coordinates: [[[77.2085, 28.6135], [77.2095, 28.6135], [77.2095, 28.6142], [77.2085, 28.6142], [77.2085, 28.6135]]]
        }
      }
    };

    return (
      <div className="map-container" style={{ width: "100%", height: "100%", minHeight: "550px", position: "relative" }}>
        <DynamicGisCanvas
          selectedMatch={syntheticMatch}
          allMatches={features.map((f) => ({
            feature_a: f.id,
            feature_a_details: f
          }))}
          onSelectMatch={(m) => onSelectFeature && onSelectFeature(m.feature_a_details)}
          basemapMode={basemap}
        />
      </div>
    );
  }

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", minHeight: "550px" }}>
      <div ref={containerRef} className="map-container" style={{ width: "100%", height: "100%", minHeight: "550px" }} />
      <div className={`map-coordinates-hud ${basemap === "dark" || basemap === "satellite" ? "dark-theme" : ""}`}>
        <span style={{ color: basemap === "dark" ? "#38bdf8" : "#2563eb", fontWeight: "700" }}>📍 EPSG:4326</span>
        <span>
          {cursorCoords
            ? `${cursorCoords.lat.toFixed(5)}°N, ${cursorCoords.lon.toFixed(5)}°E`
            : "Hover map for coordinates"}
        </span>
        {cursorCoords && (
          <span style={{ opacity: 0.8, borderLeft: "1px solid currentColor", paddingLeft: "8px" }}>
            Zoom {cursorCoords.zoom}x
          </span>
        )}
      </div>
    </div>
  );
}
