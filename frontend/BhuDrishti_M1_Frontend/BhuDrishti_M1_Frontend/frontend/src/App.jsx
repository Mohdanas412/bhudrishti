import React from "react";
import DashboardLayout from "./components/DashboardLayout";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <DashboardLayout>
      <Dashboard />
    </DashboardLayout>
  );
}
