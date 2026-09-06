import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export default function MapView({ features = [] }) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current).setView([20.5937, 78.9629], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);

    features.forEach((feature) => {
      if (
        feature.latitude !== undefined &&
        feature.longitude !== undefined
      ) {
        L.marker([feature.latitude, feature.longitude])
          .addTo(map)
          .bindPopup(
            `<strong>${feature.name || "Parcel"}</strong><br/>Status: ${
              feature.status || "Unknown"
            }`
          );
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [features]);

  return <div ref={containerRef} className="map-container" />;
}
