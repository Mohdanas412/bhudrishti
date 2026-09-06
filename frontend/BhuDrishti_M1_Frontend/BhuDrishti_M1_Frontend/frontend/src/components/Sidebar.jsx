import React from "react";

const menuItems = [
  "Dashboard",
  "Parcels",
  "Reconciliation",
  "Issues",
  "Reports"
];

export default function Sidebar({ activePage = "Dashboard" }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">BD</div>

      <nav>
        {menuItems.map((item) => (
          <button
            key={item}
            className={`nav-item ${activePage === item ? "active" : ""}`}
          >
            {item}
          </button>
        ))}
      </nav>
    </aside>
  );
}
