import React, { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

export default function MapView({ features = [] }) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: [78.9629, 20.5937],
      zoom: 4,
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    features.forEach((feature) => {
      if (feature.latitude !== undefined && feature.longitude !== undefined) {
        const popup = new maplibregl.Popup({ offset: 25 }).setHTML(
          `<strong>${feature.name || "Parcel"}</strong><br/>Status: ${
            feature.status || "Unknown"
          }`
        );

        const marker = new maplibregl.Marker()
          .setLngLat([feature.longitude, feature.latitude])
          .setPopup(popup)
          .addTo(map);

        markersRef.current.push(marker);
      }
    });
  }, [features]);

  return <div ref={containerRef} className="map-container" />;
}
