import { BrowserRouter, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import "./App.css";

import ProjectsPage from "./pages/ProjectsPage.jsx";
import UploadPage from "./pages/UploadPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";

import { api } from "./api";
import {
  getBackendEnabled,
  getSelectedProjectId,
  setBackendEnabled,
  setSelectedProjectId,
} from "./storage";

function TopBar({
  selectedProjectId,
  setSelectedProjectIdState,
  backendOk,
  setBackendOk,
  backendEnabled,
  setBackendEnabledState,
}) {
  async function refreshHealth() {
    try {
      await api.health();
      setBackendOk(true);
    } catch {
      setBackendOk(false);
    }
  }

  function disconnect() {
    setBackendEnabledState(false);
    setBackendEnabled(false);
    setBackendOk(false);
  }

  function connect() {
    setBackendEnabledState(true);
    setBackendEnabled(true);
    refreshHealth();
  }

  return (
    <div className="topbarWrap">
      <div className="topbar">
        <div className="brand">
          <div className="logo" />
          <div>
            <div className="brandTitle">RiskWise</div>
            <div className="brandSubtitle">AI Risk & Defect Prediction</div>
          </div>
        </div>

        <div className="nav">
          <NavLink to="/" end className={({ isActive }) => `tab ${isActive ? "active" : ""}`}>
            Projects
          </NavLink>
          <NavLink to="/upload" className={({ isActive }) => `tab ${isActive ? "active" : ""}`}>
            Upload
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) => `tab ${isActive ? "active" : ""}`}
          >
            Dashboard
          </NavLink>
          <NavLink to="/reports" className={({ isActive }) => `tab ${isActive ? "active" : ""}`}>
            Reports
          </NavLink>
        </div>

        <div className="right">
          <div className={`pill ${backendEnabled && backendOk ? "ok" : "bad"}`}>
            {backendEnabled && backendOk ? "Backend connected" : "Backend disconnected"}
          </div>

          {backendEnabled ? (
            <button className="btn" onClick={disconnect}>
              Disconnect
            </button>
          ) : (
            <button className="btn btnPrimary" onClick={connect}>
              Connect
            </button>
          )}

          <button className="btn" onClick={refreshHealth}>
            Refresh
          </button>

          <input
            className="input"
            style={{ width: 260 }}
            placeholder="Current Project ID"
            value={selectedProjectId}
            onChange={(e) => {
              const v = e.target.value;
              setSelectedProjectIdState(v);
              setSelectedProjectId(v);
            }}
          />
        </div>
      </div>
    </div>
  );
}

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => window.scrollTo(0, 0), [pathname]);
  return null;
}

export default function App() {
  const [selectedProjectIdState, setSelectedProjectIdState] = useState(getSelectedProjectId());
  const [backendEnabledState, setBackendEnabledState] = useState(getBackendEnabled());
  const [backendOk, setBackendOk] = useState(false);

  // initial health
  useEffect(() => {
    (async () => {
      try {
        if (!getBackendEnabled()) return setBackendOk(false);
        await api.health();
        setBackendOk(true);
      } catch {
        setBackendOk(false);
      }
    })();
  }, []);

  // sync localStorage → state (if user selects project in page)
  useEffect(() => {
    const i = setInterval(() => {
      const pid = getSelectedProjectId();
      if (pid !== selectedProjectIdState) setSelectedProjectIdState(pid);

      const be = getBackendEnabled();
      if (be !== backendEnabledState) setBackendEnabledState(be);
    }, 300);
    return () => clearInterval(i);
  }, [selectedProjectIdState, backendEnabledState]);

  const shared = useMemo(
    () => ({
      selectedProjectId: selectedProjectIdState,
      setSelectedProjectId: (id) => {
        setSelectedProjectIdState(id);
        setSelectedProjectId(id);
      },
    }),
    [selectedProjectIdState]
  );

  return (
    <BrowserRouter>
      <ScrollToTop />
      <div className="app">
        <TopBar
          selectedProjectId={selectedProjectIdState}
          setSelectedProjectIdState={setSelectedProjectIdState}
          backendOk={backendOk}
          setBackendOk={setBackendOk}
          backendEnabled={backendEnabledState}
          setBackendEnabledState={setBackendEnabledState}
        />

        <div className="container">
          <Routes>
            <Route
              path="/"
              element={<ProjectsPage onSelectProject={shared.setSelectedProjectId} />}
            />
            <Route
              path="/upload"
              element={
                <UploadPage
                  selectedProjectId={shared.selectedProjectId}
                  onSelectProject={shared.setSelectedProjectId}
                />
              }
            />
            <Route
              path="/dashboard"
              element={<DashboardPage selectedProjectId={shared.selectedProjectId} />}
            />
            <Route
              path="/reports"
              element={<ReportsPage selectedProjectId={shared.selectedProjectId} />}
            />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}