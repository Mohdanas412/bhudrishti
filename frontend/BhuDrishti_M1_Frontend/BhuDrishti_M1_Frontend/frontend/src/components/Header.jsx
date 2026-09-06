import React from "react";

export default function Header() {
  return (
    <header className="header">
      <div>
        <h1>BhuDrishti</h1>
        <p>Land Records & GIS Dashboard</p>
      </div>

      <div className="header-user">
        <span className="user-avatar">S</span>
        <span>Admin</span>
      </div>
    </header>
  );
}
