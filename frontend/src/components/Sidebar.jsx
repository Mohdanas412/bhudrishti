import React from "react";
import { NavLink } from "react-router-dom";

const menuItems = [
  { label: "Dashboard", path: "/" },
  { label: "Map", path: "/map" },
  { label: "Parcels", path: "/parcels" },
  { label: "Reconciliation", path: "/reconciliation" },
  { label: "Issues", path: "/issues" },
  { label: "Reports", path: "/reports" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">BD</div>
      <nav>
        {menuItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.path}
            className={({ isActive }) =>
              `nav-item ${isActive ? "active" : ""}`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
