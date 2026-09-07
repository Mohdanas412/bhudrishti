import React from "react";

export default function BhuDrishtiLogo({ size = 32, showText = false, subtitle = "Land Data Intelligence" }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: "10px", userSelect: "none" }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        {/* Outer shield / base parcel container */}
        <rect
          x="3"
          y="3"
          width="34"
          height="34"
          rx="8"
          fill="#f8fafc"
          stroke="#cbd5e1"
          strokeWidth="1.5"
        />

        {/* Spatial Cadastral Polygon Layer 1 (Base - Precision Blue) */}
        <path
          d="M10 14L22 9L30 15L24 23L12 21L10 14Z"
          fill="#2563eb"
          fillOpacity="0.2"
          stroke="#2563eb"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />

        {/* Spatial Municipal Polygon Layer 2 (Reconciled - Green) */}
        <path
          d="M14 18L26 13L32 21L22 31L12 27L14 18Z"
          fill="#16a34a"
          fillOpacity="0.15"
          stroke="#16a34a"
          strokeWidth="1.6"
          strokeDasharray="2 1.5"
          strokeLinejoin="round"
        />

        {/* Focal Point / Coordinate Crosshair (Vision - Drishti) */}
        <circle cx="21" cy="20" r="3" fill="#ffffff" stroke="#2563eb" strokeWidth="1.8" />
        <circle cx="21" cy="20" r="1.2" fill="#2563eb" />

        {/* Coordinate tick marks */}
        <line x1="21" y1="13" x2="21" y2="15" stroke="#93c5fd" strokeWidth="1.2" strokeLinecap="round" />
        <line x1="21" y1="25" x2="21" y2="27" stroke="#93c5fd" strokeWidth="1.2" strokeLinecap="round" />
        <line x1="14" y1="20" x2="16" y2="20" stroke="#93c5fd" strokeWidth="1.2" strokeLinecap="round" />
        <line x1="26" y1="20" x2="28" y2="20" stroke="#93c5fd" strokeWidth="1.2" strokeLinecap="round" />
      </svg>

      {showText && (
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span
            style={{
              fontSize: size > 32 ? "19px" : "15px",
              fontWeight: 800,
              letterSpacing: "-0.4px",
              color: "#172033",
              lineHeight: 1.15,
              fontFamily: "var(--font-sans, 'Inter', sans-serif)",
            }}
          >
            BhuDrishti
          </span>
          {subtitle && (
            <span
              style={{
                fontSize: "11px",
                fontWeight: 500,
                color: "#64748b",
                letterSpacing: "0.3px",
                lineHeight: 1.1,
              }}
            >
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
