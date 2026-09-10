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

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "40px", textAlign: "center", background: "#f8fafc", minHeight: "60vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: "42px", height: "42px", borderRadius: "50%", background: "#fee2e2", color: "#dc2626", display: "grid", placeItems: "center", fontSize: "20px", fontWeight: "700", marginBottom: "12px" }}>
            !
          </div>
          <h2 style={{ fontSize: "16px", fontWeight: "700", color: "#1e293b", marginBottom: "6px" }}>
            Something went wrong rendering this view
          </h2>
          <p style={{ fontSize: "12.5px", color: "#64748b", maxWidth: "450px", marginBottom: "16px", fontFamily: "monospace" }}>
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <button
            className="btn btn-primary"
            style={{ padding: "8px 16px", fontSize: "12px" }}
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
          >
            Reload Workspace
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

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
      <ErrorBoundary>
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
      </ErrorBoundary>
    </BrowserRouter>
  );
}
