import { Routes, Route, NavLink } from "react-router-dom";
import ProjectDashboard from "./pages/ProjectDashboard.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";

const navLinkStyle = ({ isActive }) => ({
  padding: "10px 12px",
  borderRadius: 14,
  border: "1px solid rgba(255,255,255,0.10)",
  background: isActive ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.06)",
  fontWeight: 800,
});

export default function App() {
  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Top bar */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          borderBottom: "1px solid rgba(255,255,255,0.10)",
          background: "rgba(7,9,15,0.65)",
          backdropFilter: "blur(10px)",
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            padding: "14px 18px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 12,
                background:
                  "linear-gradient(135deg, rgba(124,58,237,1), rgba(6,182,212,1))",
              }}
            />
            <div>
              <div style={{ fontWeight: 900 }}>RiskWise</div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>
                AI Risk & Defect Prediction
              </div>
            </div>
          </div>

          {/* Nav */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <NavLink to="/" style={navLinkStyle}>
              Projects
            </NavLink>
            <NavLink to="/upload" style={navLinkStyle}>
              Upload
            </NavLink>
            <NavLink to="/dashboard" style={navLinkStyle}>
              Dashboard
            </NavLink>
            <NavLink to="/reports" style={navLinkStyle}>
              Reports
            </NavLink>
          </div>
        </div>
      </div>

      {/* Pages */}
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: 18 }}>
        <Routes>
          <Route path="/" element={<ProjectDashboard />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/reports" element={<ReportsPage />} />
        </Routes>
      </div>
    </div>
  );
}