import React from "react";
import dashboardData from "../mock/dashboard.json";
import StatCard from "../components/StatCard";

export default function Dashboard() {
  return (
    <section>
      <div className="page-heading">
        <div>
          <h2>Dashboard</h2>
          <p>Overview of land records and parcel activity.</p>
        </div>
      </div>

      <div className="stats-grid">
        {dashboardData.stats.map((stat) => (
          <StatCard
            key={stat.title}
            title={stat.title}
            value={stat.value}
            change={stat.change}
          />
        ))}
      </div>

      <div className="dashboard-grid">
        <div className="panel map-placeholder">
          <div className="panel-header">
            <h3>GIS Map</h3>
            <span>Map module by M2</span>
          </div>
          <div className="map-box">
            <span>GIS Map Area</span>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3>Recent Activity</h3>
          </div>

          <div className="activity-list">
            {dashboardData.recentActivity.map((item) => (
              <div className="activity-item" key={item.id}>
                <div>
                  <strong>{item.action}</strong>
                  <p>{item.location}</p>
                </div>
                <span className="status-badge">{item.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
