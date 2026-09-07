import React, { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import DashboardLayout from "./components/DashboardLayout";

// Code splitting via React.lazy for GIS workstations and landing page
const LandingPage = lazy(() => import("./pages/LandingPage"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const HarmonizationWorkspace = lazy(() => import("./pages/HarmonizationWorkspace"));
const DataSourcesPage = lazy(() => import("./pages/DataSourcesPage"));
const MatchQueuePage = lazy(() => import("./pages/MatchQueuePage"));
const ConflictReviewPage = lazy(() => import("./pages/ConflictReviewPage"));
const HarmonizedResultsPage = lazy(() => import("./pages/HarmonizedResultsPage"));
const GISPage = lazy(() => import("./map/GISPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

function PageLoadingFallback() {
  return (
    <div style={{ display: "grid", placeItems: "center", height: "100%", width: "100%", padding: "60px", color: "var(--text-muted)" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
        <div style={{ width: "28px", height: "28px", border: "2.5px solid #cbd5e1", borderTopColor: "#2563eb", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
        <span style={{ fontSize: "12.5px", fontWeight: "500" }}>Loading Geospatial Canvas...</span>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoadingFallback />}>
        <Routes>
          {/* Standalone Product Landing Page */}
          <Route path="/" element={<LandingPage />} />

          {/* Workstation Application Shell Routes */}
          <Route
            path="/dashboard"
            element={
              <DashboardLayout>
                <Dashboard />
              </DashboardLayout>
            }
          />
          <Route
            path="/workspace"
            element={
              <DashboardLayout>
                <HarmonizationWorkspace />
              </DashboardLayout>
            }
          />
          <Route
            path="/datasets"
            element={
              <DashboardLayout>
                <DataSourcesPage />
              </DashboardLayout>
            }
          />
          <Route
            path="/matches"
            element={
              <DashboardLayout>
                <MatchQueuePage />
              </DashboardLayout>
            }
          />
          <Route
            path="/conflicts"
            element={
              <DashboardLayout>
                <ConflictReviewPage />
              </DashboardLayout>
            }
          />
          <Route
            path="/harmonized"
            element={
              <DashboardLayout>
                <HarmonizedResultsPage />
              </DashboardLayout>
            }
          />
          <Route
            path="/explorer"
            element={
              <DashboardLayout>
                <GISPage />
              </DashboardLayout>
            }
          />
          <Route
            path="/map"
            element={<Navigate to="/explorer" replace />}
          />
          <Route
            path="/reports"
            element={
              <DashboardLayout>
                <ReportsPage />
              </DashboardLayout>
            }
          />

          {/* Fallback to Landing Page */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
