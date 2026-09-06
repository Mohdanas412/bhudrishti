import React from "react";

export default function StatCard({ title, value, change }) {
  return (
    <div className="stat-card">
      <p className="stat-title">{title}</p>
      <h2>{value}</h2>
      <span className="stat-change">{change}</span>
    </div>
  );
}
