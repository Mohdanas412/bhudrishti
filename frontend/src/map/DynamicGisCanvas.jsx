import React, { useState, useMemo } from "react";
import { IconLayers, IconCrosshair, IconMaximize, IconCheck } from "../components/Icons";

/**
 * DynamicGisCanvas — Fallback & High-Fidelity Vector GIS Projection Engine.
 *
 * Reliably projects real EPSG:4326 GeoJSON polygons for Cadastral (Source A)
 * and Municipal (Source B) datasets with interactive zooming, panning,
 * vertex indicators, and spatial discrepancy drift vectors.
 *
 * Uses a tile-based basemap renderer (z/y/x) for reliable imagery loading,
 * instead of the ArcGIS export endpoint which has CORS/SSL issues.
 */

// ── Tile Math Helpers (Web Mercator / EPSG:3857 ↔ tile coordinates) ──
const TILE_SIZE = 256;

/** Convert latitude to Mercator Y (in range [0, 1]) */
const lat2mercY = (lat) => {
  const sinLat = Math.sin((lat * Math.PI) / 180);
  return 0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI);
};

/** Convert longitude to Mercator X (in range [0, 1]) */
const lon2mercX = (lon) => (lon + 180) / 360;

/** Convert Mercator Y back to latitude */
const mercY2lat = (y) => (180 / Math.PI) * Math.atan(Math.sinh(Math.PI * (1 - 2 * y)));

/** Determine the best zoom level for a given geographic extent and SVG dimensions */
const getBestZoom = (minLon, maxLon, minLat, maxLat, viewW, viewH) => {
  for (let z = 19; z >= 0; z--) {
    const n = Math.pow(2, z);
    const pxW = (lon2mercX(maxLon) - lon2mercX(minLon)) * n * TILE_SIZE;
    const pxH = (lat2mercY(minLat) - lat2mercY(maxLat)) * n * TILE_SIZE;
    if (pxW <= viewW * 2 && pxH <= viewH * 2) return z;
  }
  return 0;
};

export default function DynamicGisCanvas({
  selectedMatch,
  allMatches = [],
  onSelectMatch,
  layersVisibility = { cadastral: true, municipal: true },
  basemapMode = "vector",
  onToggleBasemap,
  width = 800,
  height = 500,
  showOverlays = true,
}) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [hoveredFeature, setHoveredFeature] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [cursorCoords, setCursorCoords] = useState(null);
  const isSat = basemapMode === "satellite";

  // Extract raw coordinates safely from GeoJSON
  const extractCoords = (details) => {
    if (!details?.geometry?.coordinates) return [];
    const geom = details.geometry;
    if (geom.type === "Polygon") {
      return geom.coordinates[0] || [];
    } else if (geom.type === "MultiPolygon") {
      return geom.coordinates[0]?.[0] || [];
    }
    return [];
  };

  const coordsA = useMemo(() => extractCoords(selectedMatch?.feature_a_details), [selectedMatch]);
  const coordsB = useMemo(() => extractCoords(selectedMatch?.feature_b_details), [selectedMatch]);

  // Compute spatial bounding box across active pair (plus nearby context)
  const bounds = useMemo(() => {
    const combined = [...coordsA, ...coordsB];
    if (combined.length === 0) {
      return { minLon: 77.208, maxLon: 77.212, minLat: 28.613, maxLat: 28.615 };
    }

    let minLon = Infinity, maxLon = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    combined.forEach(([lon, lat]) => {
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    });

    // Add 25% margin padding
    const lonPad = Math.max((maxLon - minLon) * 0.25, 0.0003);
    const latPad = Math.max((maxLat - minLat) * 0.25, 0.0003);

    return {
      minLon: minLon - lonPad,
      maxLon: maxLon + lonPad,
      minLat: minLat - latPad,
      maxLat: maxLat + latPad,
    };
  }, [coordsA, coordsB]);

  // Project geographic Lon/Lat to SVG viewport coordinates
  const project = (coords) => {
    if (!coords || coords.length === 0) return [];
    const { minLon, maxLon, minLat, maxLat } = bounds;
    const lonSpan = maxLon - minLon || 0.0001;
    const latSpan = maxLat - minLat || 0.0001;

    const pad = 60;
    const availW = width - pad * 2;
    const availH = height - pad * 2;

    // Aspect ratio correction for local latitude (~28° N)
    const latFactor = 1.0;
    const lonFactor = Math.cos(((minLat + maxLat) / 2) * (Math.PI / 180));
    const dataAspect = (lonSpan * lonFactor) / (latSpan * latFactor);
    const viewAspect = availW / availH;

    let scaleX, scaleY, offX, offY;
    if (dataAspect > viewAspect) {
      scaleX = availW / lonSpan;
      scaleY = (scaleX * lonFactor) / latFactor;
      offX = pad;
      offY = pad + (availH - latSpan * scaleY) / 2;
    } else {
      scaleY = availH / latSpan;
      scaleX = (scaleY * latFactor) / lonFactor;
      offY = pad;
      offX = pad + (availW - lonSpan * scaleX) / 2;
    }

    return coords.map(([lon, lat]) => {
      const x = offX + (lon - minLon) * scaleX;
      const y = offY + (maxLat - lat) * scaleY;
      return [x, y];
    });
  };

  const polyPointsA = useMemo(() => {
    const pts = project(coordsA);
    return pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  }, [coordsA, bounds, width, height]);

  const polyPointsB = useMemo(() => {
    const pts = project(coordsB);
    return pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  }, [coordsB, bounds, width, height]);

  const ptsA = useMemo(() => project(coordsA), [coordsA, bounds, width, height]);
  const ptsB = useMemo(() => project(coordsB), [coordsB, bounds, width, height]);

  // Unproject SVG coordinates back to Geographic Lon/Lat (EPSG:4326)
  const unproject = (svgX, svgY) => {
    const { minLon, maxLon, minLat, maxLat } = bounds;
    const lonSpan = maxLon - minLon || 0.0001;
    const latSpan = maxLat - minLat || 0.0001;
    const pad = 60;
    const availW = width - pad * 2;
    const availH = height - pad * 2;
    const latFactor = 1.0;
    const lonFactor = Math.cos(((minLat + maxLat) / 2) * (Math.PI / 180));
    const dataAspect = (lonSpan * lonFactor) / (latSpan * latFactor);
    const viewAspect = availW / availH;

    let scaleX, scaleY, offX, offY;
    if (dataAspect > viewAspect) {
      scaleX = availW / lonSpan;
      scaleY = (scaleX * lonFactor) / latFactor;
      offX = pad;
      offY = pad + (availH - latSpan * scaleY) / 2;
    } else {
      scaleY = availH / latSpan;
      scaleX = (scaleY * latFactor) / lonFactor;
      offY = pad;
      offX = pad + (availW - lonSpan * scaleX) / 2;
    }

    const lon = minLon + (svgX - offX) / scaleX;
    const lat = maxLat - (svgY - offY) / scaleY;
    return { lon, lat };
  };

  // Centroid calculation
  const centroidA = useMemo(() => {
    if (ptsA.length === 0) return null;
    const sum = ptsA.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
    return [sum[0] / ptsA.length, sum[1] / ptsA.length];
  }, [ptsA]);

  const centroidB = useMemo(() => {
    if (ptsB.length === 0) return null;
    const sum = ptsB.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
    return [sum[0] / ptsB.length, sum[1] / ptsB.length];
  }, [ptsB]);

  // Spatial shift distance in meters
  const shiftDistanceMeters = useMemo(() => {
    if (!coordsA.length || !coordsB.length) return null;
    const cA = coordsA.reduce((acc, [lon, lat]) => [acc[0] + lon, acc[1] + lat], [0, 0]);
    const cB = coordsB.reduce((acc, [lon, lat]) => [acc[0] + lon, acc[1] + lat], [0, 0]);
    const lonA = cA[0] / coordsA.length, latA = cA[1] / coordsA.length;
    const lonB = cB[0] / coordsB.length, latB = cB[1] / coordsB.length;
    const dLat = (latB - latA) * 111139;
    const dLon = (lonB - lonA) * 111139 * Math.cos(((latA + latB) / 2) * (Math.PI / 180));
    return Math.sqrt(dLat * dLat + dLon * dLon).toFixed(1);
  }, [coordsA, coordsB]);

  // Pan & Drag handlers
  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      setPanOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }

    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;

    const centerX = width / 2;
    const centerY = height / 2;
    const svgX = (clientX - panOffset.x - centerX) / zoomLevel + centerX;
    const svgY = (clientY - panOffset.y - centerY) / zoomLevel + centerY;

    const coords = unproject(svgX, svgY);
    setCursorCoords(coords);
  };

  const handleMouseUp = () => setIsDragging(false);

  // Scroll wheel zoom — zooms toward the cursor position
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.15 : 0.15;
    setZoomLevel((z) => Math.min(Math.max(z + delta, 0.4), 5));
  };

  const resetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Surrounding contextual parcels (up to 6)
  const surroundingParcels = useMemo(() => {
    if (!allMatches || allMatches.length <= 1) return [];
    return allMatches
      .filter((m) => m.feature_a !== selectedMatch?.feature_a && m.feature_a_details?.geometry)
      .slice(0, 6)
      .map((m) => {
        const coords = extractCoords(m.feature_a_details);
        const pts = project(coords);
        return {
          match: m,
          points: pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "),
          pts,
        };
      })
      .filter((p) => p.points.length > 0);
  }, [allMatches, selectedMatch, bounds, width, height]);

  // ── Tile-based Basemap: compute tiles that cover the current bounds ──
  const basemapTiles = useMemo(() => {
    const { minLon, maxLon, minLat, maxLat } = bounds;
    const z = getBestZoom(minLon, maxLon, minLat, maxLat, width, height);
    const n = Math.pow(2, z);

    // Tile indices covering the bounding box
    const xMin = Math.floor(lon2mercX(minLon) * n);
    const xMax = Math.floor(lon2mercX(maxLon) * n);
    const yMin = Math.floor(lat2mercY(maxLat) * n); // maxLat → lower tile row
    const yMax = Math.floor(lat2mercY(minLat) * n); // minLat → higher tile row

    // Tile URL template based on basemap mode
    const tileBase = isSat
      ? "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile"
      : "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile";

    const tiles = [];
    for (let ty = yMin; ty <= yMax; ty++) {
      for (let tx = xMin; tx <= xMax; tx++) {
        // Geographic bounds of this tile
        const tileLonMin = (tx / n) * 360 - 180;
        const tileLonMax = ((tx + 1) / n) * 360 - 180;
        const tileLatMax = mercY2lat(ty / n);
        const tileLatMin = mercY2lat((ty + 1) / n);

        // Project tile corners to SVG coordinates using our existing projection
        const topLeft = project([[tileLonMin, tileLatMax]])[0];
        const bottomRight = project([[tileLonMax, tileLatMin]])[0];

        if (!topLeft || !bottomRight) continue;

        const tileX = topLeft[0];
        const tileY = topLeft[1];
        const tileW = bottomRight[0] - topLeft[0];
        const tileH = bottomRight[1] - topLeft[1];

        tiles.push({
          key: `${z}-${tx}-${ty}`,
          url: `${tileBase}/${z}/${ty}/${tx}`,
          x: tileX,
          y: tileY,
          w: tileW,
          h: tileH,
        });
      }
    }
    return tiles;
  }, [bounds, width, height, isSat]);

  return (
    <div
      className="dynamic-gis-canvas"
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        minHeight: "420px",
        background: isSat
          ? "#0b0f19"
          : "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)",
        overflow: "hidden",
        userSelect: "none",
        cursor: isDragging ? "grabbing" : "grab",
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Always-visible Zoom Controls */}
      <div
        style={{
          position: "absolute",
          bottom: "16px",
          left: "16px",
          zIndex: 20,
          display: "flex",
          flexDirection: "column",
          gap: "2px",
          background: isSat ? "rgba(15, 23, 42, 0.9)" : "rgba(255, 255, 255, 0.95)",
          backdropFilter: "blur(12px)",
          border: isSat ? "1px solid rgba(255, 255, 255, 0.15)" : "1px solid #e2e8f0",
          borderRadius: "8px",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
          overflow: "hidden",
        }}
      >
        <button
          style={{
            width: "34px",
            height: "34px",
            border: "none",
            background: "transparent",
            cursor: "pointer",
            fontSize: "18px",
            fontWeight: "700",
            color: isSat ? "#f8fafc" : "#1e293b",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = isSat ? "rgba(255,255,255,0.1)" : "#f1f5f9"}
          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
          onClick={(e) => {
            e.stopPropagation();
            setZoomLevel((z) => Math.min(z + 0.25, 5));
          }}
          title="Zoom In"
        >
          +
        </button>
        <div style={{ height: "1px", background: isSat ? "rgba(255,255,255,0.12)" : "#e2e8f0", margin: "0 6px" }} />
        <button
          style={{
            width: "34px",
            height: "34px",
            border: "none",
            background: "transparent",
            cursor: "pointer",
            fontSize: "18px",
            fontWeight: "700",
            color: isSat ? "#f8fafc" : "#1e293b",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = isSat ? "rgba(255,255,255,0.1)" : "#f1f5f9"}
          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
          onClick={(e) => {
            e.stopPropagation();
            setZoomLevel((z) => Math.max(z - 0.25, 0.4));
          }}
          title="Zoom Out"
        >
          −
        </button>
        <div style={{ height: "1px", background: isSat ? "rgba(255,255,255,0.12)" : "#e2e8f0", margin: "0 6px" }} />
        <button
          style={{
            width: "34px",
            height: "30px",
            border: "none",
            background: "transparent",
            cursor: "pointer",
            fontSize: "10px",
            fontWeight: "700",
            color: isSat ? "#94a3b8" : "#64748b",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            letterSpacing: "0.3px",
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = isSat ? "rgba(255,255,255,0.1)" : "#f1f5f9"}
          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
          onClick={(e) => {
            e.stopPropagation();
            resetView();
          }}
          title="Reset View"
        >
          FIT
        </button>
      </div>
      {/* Top Floating Extent Header - Only shown in standalone mode */}
      {showOverlays && (
        <div
          style={{
            position: "absolute",
            top: "14px",
            right: "14px",
            zIndex: 10,
            display: "flex",
            gap: "8px",
            alignItems: "center",
            background: isSat ? "rgba(15, 23, 42, 0.88)" : "rgba(255, 255, 255, 0.95)",
            backdropFilter: "blur(14px)",
            border: isSat ? "1px solid rgba(255, 255, 255, 0.14)" : "1px solid var(--border-subtle, #e2e8f0)",
            borderRadius: "8px",
            padding: "6px 12px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.12)",
            color: isSat ? "#f8fafc" : "#1e293b",
          }}
        >
          <div style={{ display: "flex", gap: "2px", background: isSat ? "rgba(30, 41, 59, 0.8)" : "#f1f5f9", borderRadius: "6px", padding: "2px" }}>
            <button
              style={{
                padding: "2px 8px",
                fontSize: "11px",
                height: "22px",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                fontWeight: basemapMode === "vector" ? "700" : "500",
                background: basemapMode === "vector" ? "#ffffff" : "transparent",
                color: basemapMode === "vector" ? "#1e293b" : (isSat ? "#94a3b8" : "#64748b"),
                boxShadow: basemapMode === "vector" ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
              }}
              onClick={(e) => {
                e.stopPropagation();
                onToggleBasemap && onToggleBasemap("vector");
              }}
            >
              Street Map
            </button>
            <button
              style={{
                padding: "2px 8px",
                fontSize: "11px",
                height: "22px",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                fontWeight: basemapMode === "satellite" ? "700" : "500",
                background: basemapMode === "satellite" ? "#ffffff" : "transparent",
                color: basemapMode === "satellite" ? "#1e293b" : (isSat ? "#94a3b8" : "#64748b"),
                boxShadow: basemapMode === "satellite" ? "0 1px 2px rgba(0,0,0,0.1)" : "none",
              }}
              onClick={(e) => {
                e.stopPropagation();
                onToggleBasemap && onToggleBasemap("satellite");
              }}
            >
              🛰️ Satellite (Esri)
            </button>
          </div>

          <div style={{ height: "14px", width: "1px", background: isSat ? "rgba(255, 255, 255, 0.2)" : "#cbd5e1" }}></div>

          <div style={{ fontSize: "11.5px", color: isSat ? "#94a3b8" : "#64748b" }}>
            Extent: <span style={{ fontFamily: "monospace", fontWeight: "600", color: isSat ? "#38bdf8" : "#1e293b" }}>EPSG:4326</span>
          </div>
          <div style={{ height: "14px", width: "1px", background: isSat ? "rgba(255, 255, 255, 0.2)" : "#cbd5e1" }}></div>
          <button
            className="btn btn-secondary btn-sm"
            style={{ padding: "2px 6px", fontSize: "12px", height: "24px" }}
            onClick={(e) => {
              e.stopPropagation();
              setZoomLevel((z) => Math.min(z + 0.25, 3));
            }}
            title="Zoom In"
          >
            +
          </button>
          <button
            className="btn btn-secondary btn-sm"
            style={{ padding: "2px 6px", fontSize: "12px", height: "24px" }}
            onClick={(e) => {
              e.stopPropagation();
              setZoomLevel((z) => Math.max(z - 0.25, 0.6));
            }}
            title="Zoom Out"
          >
            −
          </button>
          <button
            className="btn btn-secondary btn-sm"
            style={{ padding: "2px 8px", fontSize: "11px", height: "24px", display: "flex", alignItems: "center", gap: "4px" }}
            onClick={(e) => {
              e.stopPropagation();
              resetView();
            }}
            title="Reset Zoom & Extent"
          >
            <IconMaximize size={12} /> Fit
          </button>
        </div>
      )}

      {/* Interactive SVG Projection Plane */}
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${width} ${height}`}
        style={{
          transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
          transformOrigin: "center center",
          transition: isDragging ? "none" : "transform 0.15s ease-out",
        }}
      >
        <defs>
          <clipPath id="canvasClip">
            <rect x="0" y="0" width={width} height={height} />
          </clipPath>
          <pattern id="gisGrid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="0.8" />
          </pattern>
          <pattern id="gisGridDark" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(56, 189, 248, 0.12)" strokeWidth="0.8" />
          </pattern>
          <filter id="neonCyanGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="3.5" floodColor="#38bdf8" floodOpacity="0.8" />
          </filter>
          <filter id="neonEmeraldGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="3.5" floodColor="#4ade80" floodOpacity="0.8" />
          </filter>
          <filter id="neonRoseGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#f43f5e" floodOpacity="0.85" />
          </filter>
          <linearGradient id="cadastralGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0.15" />
          </linearGradient>
          <linearGradient id="municipalGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#16a34a" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#15803d" stopOpacity="0.12" />
          </linearGradient>
        </defs>

        {/* Basemap Background: Tile-Based z/y/x Rendering */}
        <g clipPath="url(#canvasClip)">
          {basemapTiles.map((tile) => (
            <image
              key={tile.key}
              href={tile.url}
              x={tile.x}
              y={tile.y}
              width={tile.w}
              height={tile.h}
              preserveAspectRatio="none"
              style={{ imageRendering: "auto" }}
            />
          ))}
        </g>

        {/* Surrounding Context Parcels */}
        {surroundingParcels.map((sp, idx) => (
          <g key={`surround-${idx}`} style={{ cursor: "pointer" }} onClick={() => onSelectMatch && onSelectMatch(sp.match)}>
            <polygon
              points={sp.points}
              fill="rgba(203, 213, 225, 0.25)"
              stroke="#94a3b8"
              strokeWidth="1.2"
              strokeDasharray="3 2"
            />
            {sp.pts[0] && (
              <text
                x={sp.pts[0][0] + 4}
                y={sp.pts[0][1] - 4}
                fontSize="9"
                fill="#475569"
                fontWeight="600"
                fontFamily="sans-serif"
              >
                {sp.match.feature_a}
              </text>
            )}
          </g>
        ))}

        {/* Municipal Parcel (Source B) Polygon */}
        {layersVisibility.municipal && polyPointsB && (
          <g>
            <polygon
              points={polyPointsB}
              fill="rgba(34, 197, 94, 0.28)"
              stroke="#16a34a"
              strokeWidth="2.5"
              strokeDasharray="5 3"
              onMouseEnter={() => setHoveredFeature("municipal")}
              onMouseLeave={() => setHoveredFeature(null)}
            />
            {/* Source B Vertices */}
            {ptsB.map(([x, y], idx) => (
              <rect
                key={`v-b-${idx}`}
                x={x - 3.5}
                y={y - 3.5}
                width="7"
                height="7"
                fill="#16a34a"
                stroke="#ffffff"
                strokeWidth="1.5"
              />
            ))}
          </g>
        )}

        {/* Cadastral Parcel (Source A - Legal Baseline) Polygon */}
        {layersVisibility.cadastral && polyPointsA && (
          <g>
            <polygon
              points={polyPointsA}
              fill="rgba(59, 130, 246, 0.35)"
              stroke="#2563eb"
              strokeWidth="3.0"
              onMouseEnter={() => setHoveredFeature("cadastral")}
              onMouseLeave={() => setHoveredFeature(null)}
            />
            {/* Source A Vertices */}
            {ptsA.map(([x, y], idx) => (
              <circle
                key={`v-a-${idx}`}
                cx={x}
                cy={y}
                r="4.5"
                fill="#1d4ed8"
                stroke="#ffffff"
                strokeWidth="1.8"
              />
            ))}
          </g>
        )}

        {/* Centroid Discrepancy Drift Vector & Radar Pulse */}
        {centroidA && centroidB && (
          <g>
            <line
              x1={centroidA[0]}
              y1={centroidA[1]}
              x2={centroidB[0]}
              y2={centroidB[1]}
              stroke="#f43f5e"
              strokeWidth="2.2"
              strokeDasharray="3 2"
            />

            {/* Radar Pulsing Rings around Discrepancy Pin */}
            <circle cx={centroidA[0]} cy={centroidA[1]} r="6" fill="none" stroke="#2563eb" strokeWidth="1.5" opacity="0.8">
              <animate attributeName="r" values="6;20;6" dur="2.2s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.8;0;0.8" dur="2.2s" repeatCount="indefinite" />
            </circle>
            <circle cx={centroidB[0]} cy={centroidB[1]} r="6" fill="none" stroke="#16a34a" strokeWidth="1.5" opacity="0.8">
              <animate attributeName="r" values="6;20;6" dur="2.2s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.8;0;0.8" dur="2.2s" repeatCount="indefinite" />
            </circle>

            {/* Source A Centroid Pin */}
            <circle cx={centroidA[0]} cy={centroidA[1]} r="5.5" fill="#2563eb" stroke="#ffffff" strokeWidth="2" />
            {/* Source B Centroid Pin */}
            <circle cx={centroidB[0]} cy={centroidB[1]} r="5.5" fill="#16a34a" stroke="#ffffff" strokeWidth="2" />

            {/* Discrepancy Shift Label */}
            <rect
              x={(centroidA[0] + centroidB[0]) / 2 - 46}
              y={(centroidA[1] + centroidB[1]) / 2 - 20}
              width="92"
              height="18"
              rx="4"
              fill={isSat ? "rgba(15, 23, 42, 0.92)" : "#ffffff"}
              stroke={isSat ? "#f43f5e" : "#fca5a5"}
              strokeWidth="1.2"
            />
            <text
              x={(centroidA[0] + centroidB[0]) / 2}
              y={(centroidA[1] + centroidB[1]) / 2 - 7}
              textAnchor="middle"
              fontSize="9"
              fontWeight="700"
              fill={isSat ? "#fda4af" : "#b91c1c"}
              fontFamily="sans-serif"
            >
              {shiftDistanceMeters ? `Δ Shift: ${shiftDistanceMeters}m` : "Δ Spatial Shift"}
            </text>
          </g>
        )}

        {/* Coordinate Axis Reference Ticks */}
        <text x="14" y="24" fontSize="10" fill={isSat ? "#ffffff" : "#475569"} fontFamily="monospace" fontWeight="600" style={{ textShadow: isSat ? "0 1px 3px rgba(0,0,0,0.9)" : "none" }}>
          {bounds.maxLat.toFixed(5)}°N
        </text>
        <text x="14" y={height - 14} fontSize="10" fill={isSat ? "#ffffff" : "#475569"} fontFamily="monospace" fontWeight="600" style={{ textShadow: isSat ? "0 1px 3px rgba(0,0,0,0.9)" : "none" }}>
          {bounds.minLat.toFixed(5)}°N
        </text>
        <text x={width - 85} y={height - 14} fontSize="10" fill={isSat ? "#ffffff" : "#475569"} fontFamily="monospace" fontWeight="600" style={{ textShadow: isSat ? "0 1px 3px rgba(0,0,0,0.9)" : "none" }}>
          {bounds.maxLon.toFixed(5)}°E
        </text>
      </svg>

      {/* Overlays (Coordinate HUD & Symbology Legend) - Only in standalone mode */}
      {showOverlays && (
        <>
          {/* Bottom Left: Live Coordinate HUD */}
          <div className={`map-coordinates-hud ${isSat ? "dark-theme" : ""}`}>
            <span style={{ color: "#2563eb", fontWeight: "700" }}>📍 EPSG:4326</span>
            <span>
              {cursorCoords
                ? `${cursorCoords.lat.toFixed(5)}°N, ${cursorCoords.lon.toFixed(5)}°E`
                : "Hover canvas for coordinates"}
            </span>
            <span style={{ opacity: 0.8, borderLeft: "1px solid currentColor", paddingLeft: "8px" }}>
              Zoom {zoomLevel.toFixed(1)}x
            </span>
          </div>

          {/* Bottom Right: Floating Interactive Legend */}
          <div className={`map-floating-legend ${isSat ? "dark-theme" : ""}`}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <span style={{ fontWeight: "700", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Inspection Symbology
              </span>
              <strong style={{ color: selectedMatch?.score >= 90 ? "#16a34a" : "#d97706", fontFamily: "monospace", fontSize: "11px" }}>
                Match {selectedMatch?.score || 0}%
              </strong>
            </div>

            <div className="legend-row">
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "12px", height: "12px", borderRadius: "3px", background: "#2563eb", display: "inline-block" }}></span>
                <span>Cadastral: {selectedMatch?.feature_a || "N/A"}</span>
              </div>
              <span style={{ fontSize: "10.5px", opacity: 0.75 }}>
                {selectedMatch?.feature_a_details?.area || "—"} m²
              </span>
            </div>

            <div className="legend-row">
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "12px", height: "12px", borderRadius: "3px", border: "2px dashed #16a34a", background: "rgba(22, 163, 74, 0.2)", display: "inline-block" }}></span>
                <span>Municipal: {selectedMatch?.feature_b || "N/A"}</span>
              </div>
              <span style={{ fontSize: "10.5px", opacity: 0.75 }}>
                {selectedMatch?.feature_b_details?.area || "—"} m²
              </span>
            </div>

            {shiftDistanceMeters && (
              <div className="legend-row" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "4px", marginTop: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#f43f5e" }}>
                  <span style={{ width: "10px", height: "3px", background: "#f43f5e", display: "inline-block" }}></span>
                  <span>Spatial Centroid Drift:</span>
                </div>
                <strong style={{ fontFamily: "monospace", color: "#f43f5e" }}>
                  {shiftDistanceMeters} m
                </strong>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
