import React, { useEffect, useState } from "react";
import MapView from "./MapView";
import LayerControl from "./LayerControl";
import MapLegend from "./MapLegend";
import FeaturePanel from "./FeaturePanel";
import { api } from "../services/api";
import { IconSearch, IconMaximize } from "../components/Icons";

/**
 * GIS Explorer — map-first spatial inspection page.
 *
 * Control zones (no overlaps):
 *   Top toolbar   — basemap toggle + parcel search button
 *   Left (in-map) — layer switcher (LayerControl)
 *   Right (in-map)— feature details panel, positioned below MapLibre nav
 *   Bottom-right  — legend
 *
 * Parcel search opens as a slide-down panel in the top toolbar row,
 * NOT as a floating card on the map, eliminating the previous collision
 * with LayerControl at top:15px / left:15px.
 */
export default function GISPage() {
  const [features, setFeatures] = useState([]);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [basemap, setBasemap] = useState("vector");
  const [searchOpen, setSearchOpen] = useState(false);
  const [khasraQuery, setKhasraQuery] = useState("");
  const [khasraResult, setKhasraResult] = useState(null);

  const [layers, setLayers] = useState([
    { id: "cadastral", name: "Cadastral Parcels", visible: true },
    { id: "municipal", name: "Municipal Boundaries", visible: true },
    { id: "issues",    name: "Discrepancy Hotspots", visible: true }
  ]);

  useEffect(() => {
    async function load() {
      const [matches, hotspotsData] = await Promise.all([
        api.getMatches(),
        api.getHotspots(),
      ]);
      const loadedFeats = [];
      matches.forEach((m) => {
        if (m.feature_a_details?.geometry) {
          loadedFeats.push({
            id: m.feature_a,
            name: `Cadastral ${m.feature_a}`,
            status: m.status === "matched" ? "Verified" : "Review Required",
            type: "cadastral",
            area: `${m.feature_a_details.area || ""} m²`,
            geometry: m.feature_a_details.geometry,
            owner: m.feature_a_details.owner,
            land_use: m.feature_a_details.land_use,
          });
        }
        if (m.feature_b_details?.geometry) {
          loadedFeats.push({
            id: m.feature_b,
            name: `Municipal ${m.feature_b}`,
            status: "Municipal Source",
            type: "municipal",
            area: `${m.feature_b_details.area || ""} m²`,
            geometry: m.feature_b_details.geometry,
            owner: m.feature_b_details.owner || m.feature_b_details.address,
            land_use: m.feature_b_details.zone || "Municipal Zone",
          });
        }
      });

      (hotspotsData?.hotspots || []).forEach((h) => {
        if (h.center && h.center.length >= 2) {
          loadedFeats.push({
            id: `HOTSPOT-${h.cluster_id}`,
            name: `Discrepancy Hotspot #${h.cluster_id}`,
            status: `${h.conflict_count} Conflicts (${h.severity})`,
            type: "issues",
            severity: h.severity,
            latitude: h.center[1],
            longitude: h.center[0],
            geometry: {
              type: "Point",
              coordinates: [h.center[0], h.center[1]]
            }
          });
        }
      });

      setFeatures(loadedFeats);
      if (loadedFeats.length > 0) setSelectedFeature(loadedFeats[0]);
    }
    load();
  }, []);

  const toggleLayer = (id) => {
    setLayers((curr) => curr.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)));
  };

  const handleKhasraSearch = (e) => {
    e.preventDefault();
    setKhasraResult(null);
    const q = khasraQuery.trim().toLowerCase();
    if (!q) return;
    const found = features.find(
      (f) =>
        f.id.toLowerCase().includes(q) ||
        (f.owner && f.owner.toLowerCase().includes(q)) ||
        (f.land_use && f.land_use.toLowerCase().includes(q))
    );
    if (found) {
      setKhasraResult({ type: "found", feature: found });
      setSelectedFeature(found);
    } else {
      setKhasraResult({ type: "not_found" });
    }
  };

  return (
    <div className="content-full" style={{ position: "relative", flexDirection: "column" }}>
      {/* ── Top Toolbar ── */}
      <div style={{
        height: "auto",
        background: "var(--bg-surface)",
        borderBottom: "1px solid var(--border-subtle)",
        zIndex: 20,
        flexShrink: 0,
      }}>
        {/* Main toolbar row */}
        <div style={{
          height: 48,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 20px",
        }}>
          <div>
            <span style={{ fontSize: "13.5px", fontWeight: "700", color: "var(--text-primary)" }}>
              GIS Explorer
            </span>
            <span style={{ marginLeft: "10px", fontSize: "11.5px", color: "var(--text-muted)" }}>
              Spatial Inspection Canvas · EPSG:4326
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => { setSearchOpen(!searchOpen); setKhasraResult(null); setKhasraQuery(""); }}
              aria-expanded={searchOpen}
              aria-controls="khasra-search-bar"
            >
              <IconSearch size={13} />
              {searchOpen ? "Close Search" : "Search Khasra / Parcel"}
            </button>

            <div className="filter-chip-group">
              <button
                className={`filter-chip ${basemap === "vector" ? "active" : ""}`}
                onClick={() => setBasemap("vector")}
                title="Standard Vector GIS Basemap"
              >
                Vector
              </button>
              <button
                className={`filter-chip ${basemap === "satellite" ? "active" : ""}`}
                onClick={() => setBasemap("satellite")}
                title="ArcGIS World Imagery Satellite Basemap"
              >
                🛰️ Satellite (Esri)
              </button>
              <button
                className={`filter-chip ${basemap === "dark" ? "active" : ""}`}
                onClick={() => setBasemap("dark")}
                title="Dark Matter Cyber GIS Basemap"
              >
                🌙 Dark GIS
              </button>
            </div>
          </div>
        </div>

        {/* Expandable search bar — in toolbar, not on map */}
        {searchOpen && (
          <div
            id="khasra-search-bar"
            style={{
              borderTop: "1px solid var(--border-subtle)",
              padding: "10px 20px",
              background: "var(--bg-surface-subtle)",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              flexWrap: "wrap",
            }}
          >
            <form onSubmit={handleKhasraSearch} style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
              <input
                type="text"
                placeholder="Search by Parcel ID, owner name, or land use (e.g. P-102)"
                value={khasraQuery}
                onChange={(e) => setKhasraQuery(e.target.value)}
                style={{
                  width: "320px",
                  padding: "6px 10px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--border-strong)",
                  fontSize: "12.5px",
                  background: "var(--bg-surface)",
                }}
                autoFocus
              />
              <button type="submit" className="btn btn-primary btn-sm">
                Search &amp; Zoom
              </button>
            </form>

            {khasraResult?.type === "found" && (
              <div style={{
                padding: "5px 12px",
                background: "var(--color-success-bg)",
                border: "1px solid var(--color-success-border)",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                color: "var(--color-success-text)",
                display: "flex",
                gap: "8px",
              }}>
                <strong>Found:</strong>
                <span>{khasraResult.feature.name}</span>
                <span>·</span>
                <span>{khasraResult.feature.owner}</span>
                <span>·</span>
                <span>{khasraResult.feature.area}</span>
              </div>
            )}
            {khasraResult?.type === "not_found" && (
              <div style={{
                padding: "5px 12px",
                background: "var(--color-danger-bg)",
                border: "1px solid var(--color-danger-border)",
                borderRadius: "var(--radius-sm)",
                fontSize: "12px",
                color: "var(--color-danger-text)",
              }}>
                No matching parcel found.
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Map Canvas ── fills the rest of the viewport height ── */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden", minHeight: 0 }}>
        {(() => {
          const visibleLayerIds = new Set(layers.filter((l) => l.visible).map((l) => l.id));
          const displayedFeatures = features.filter((f) => visibleLayerIds.has(f.type));
          return (
            <MapView
              features={displayedFeatures}
              basemap={basemap}
              selectedFeature={selectedFeature}
              onSelectFeature={setSelectedFeature}
            />
          );
        })()}
        <LayerControl layers={layers} onToggle={toggleLayer} />
        <MapLegend />
        {selectedFeature && (
          <FeaturePanel
            feature={selectedFeature}
            onClose={() => setSelectedFeature(null)}
          />
        )}
      </div>
    </div>
  );
}
