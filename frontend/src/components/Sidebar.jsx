import React, { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import BhuDrishtiLogo from "./BhuDrishtiLogo";
import {
  IconDashboard,
  IconWorkspace,
  IconDataSources,
  IconMatchQueue,
  IconConflicts,
  IconHarmonized,
  IconGISExplorer,
  IconReports,
  IconChevronLeft,
  IconChevronRight
} from "./Icons";
import { api } from "../services/api";

export default function Sidebar({ collapsed, onToggleCollapse }) {
  const [conflictCount, setConflictCount] = useState(1);
  const [datasetCount, setDatasetCount] = useState(3);

  useEffect(() => {
    async function loadCounts() {
      const [conflicts, datasets] = await Promise.all([
        api.getConflicts(),
        api.getDatasets(),
      ]);
      const unresolved = conflicts.filter((c) => c.status !== "resolved");
      setConflictCount(unresolved.length);
      setDatasetCount(datasets.length);
    }
    loadCounts();
  }, []);

  return (
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      {/* Brand Header */}
      <div className="sidebar-header">
        <NavLink to="/" className="sidebar-header-link" title="BhuDrishti Home">
          <BhuDrishtiLogo size={28} showText={!collapsed} subtitle="Land Data Intelligence" />
        </NavLink>
        <button
          className="sidebar-collapse-btn"
          onClick={onToggleCollapse}
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          style={{ width: "24px", height: "24px", padding: 0 }}
        >
          {collapsed ? <IconChevronRight size={14} /> : <IconChevronLeft size={14} />}
        </button>
      </div>

      {/* Light Navigation Links */}
      <nav className="sidebar-nav">
        {/* OVERVIEW */}
        {!collapsed && <span className="nav-section-title">Overview</span>}
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="Dashboard"
        >
          <div className="nav-link-content">
            <IconDashboard size={17} />
            {!collapsed && <span>Dashboard</span>}
          </div>
        </NavLink>

        {/* DATA */}
        {!collapsed && <span className="nav-section-title" style={{ marginTop: "10px" }}>Data</span>}
        <NavLink
          to="/datasets"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="Data Sources"
        >
          <div className="nav-link-content">
            <IconDataSources size={17} />
            {!collapsed && <span>Data Sources</span>}
          </div>
          {!collapsed && datasetCount > 0 && <span className="nav-badge">{datasetCount}</span>}
        </NavLink>

        {/* HARMONIZATION */}
        {!collapsed && <span className="nav-section-title" style={{ marginTop: "10px" }}>Harmonization</span>}
        <NavLink
          to="/workspace"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="Workspace"
        >
          <div className="nav-link-content">
            <IconWorkspace size={17} />
            {!collapsed && <span>Workspace</span>}
          </div>
        </NavLink>

        <NavLink
          to="/matches"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="Match Review"
        >
          <div className="nav-link-content">
            <IconMatchQueue size={17} />
            {!collapsed && <span>Match Review</span>}
          </div>
        </NavLink>

        <NavLink
          to="/conflicts"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="Conflicts"
        >
          <div className="nav-link-content">
            <IconConflicts size={17} />
            {!collapsed && <span>Conflicts</span>}
          </div>
          {!collapsed && conflictCount > 0 && (
            <span className="nav-badge danger">{conflictCount}</span>
          )}
        </NavLink>

        {/* OUTPUT */}
        {!collapsed && <span className="nav-section-title" style={{ marginTop: "10px" }}>Output</span>}
        <NavLink
          to="/harmonized"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="Harmonized Data"
        >
          <div className="nav-link-content">
            <IconHarmonized size={17} />
            {!collapsed && <span>Harmonized Data</span>}
          </div>
        </NavLink>

        <NavLink
          to="/explorer"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="GIS Explorer"
        >
          <div className="nav-link-content">
            <IconGISExplorer size={17} />
            {!collapsed && <span>GIS Explorer</span>}
          </div>
        </NavLink>

        <NavLink
          to="/reports"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title="Reports"
        >
          <div className="nav-link-content">
            <IconReports size={17} />
            {!collapsed && <span>Reports</span>}
          </div>
        </NavLink>
      </nav>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-status-box">
          {!collapsed && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className="status-dot" style={{ background: "#16a34a" }}></span>
              <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>EPSG:4326 GIS Engine</span>
            </div>
          )}
          <span style={{ fontSize: "10px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>v0.3.0</span>
        </div>
      </div>
    </aside>
  );
}
