import { useState } from "react";
import { api } from "../api";

export default function DashboardPage({ selectedProjectId }) {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const [riskScore, setRiskScore] = useState(0.74);
  const [riskLevel, setRiskLevel] = useState("High");
  const [predictedDefects, setPredictedDefects] = useState(12);
  const [hotspot, setHotspot] = useState("auth.py");
  const [drivers, setDrivers] = useState(["High churn", "Low test coverage", "Large commits"]);

  async function refresh() {
    setErr("");
    setMsg("");

    if (!selectedProjectId) {
      setErr("No project selected. Go to Projects and click Select.");
      return;
    }

    setLoading(true);
    try {
      const d = await api.getDashboard(selectedProjectId);

      // accept flexible backend response shapes
      const rs = d.risk_score ?? d.riskScore ?? d.score;
      const rl = d.risk_level ?? d.riskLevel ?? d.level;
      const pd = d.predicted_defects ?? d.predictedDefects ?? d.defects;
      const hs = d.hotspot ?? d.hotspot_file ?? d.hotspotFile;
      const td = d.top_drivers ?? d.topDrivers ?? d.drivers;

      if (rs != null) setRiskScore(Number(rs));
      if (rl) setRiskLevel(String(rl));
      if (pd != null) setPredictedDefects(Number(pd));
      if (hs) setHotspot(String(hs));
      if (Array.isArray(td)) setDrivers(td.map(String));

      setMsg("Dashboard refreshed ✅");
    } catch {
      setMsg("Backend dashboard not ready — showing mock preview ✅");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="title">Dashboard</div>
      <p className="sub">Mock preview (replace with API later)</p>

      {err && <div className="notice bad">{err}</div>}
      {msg && <div className="notice ok">{msg}</div>}

      <div className="cardRow">
        <div className="smallCard">
          <div className="mutedSmall">Risk Score</div>
          <div className="bigNum">{Number(riskScore).toFixed(2)}</div>
          <div className="muted">Level: <b>{riskLevel}</b></div>
        </div>

        <div className="smallCard">
          <div className="mutedSmall">Predicted Defects</div>
          <div className="bigNum">{predictedDefects}</div>
          <div className="muted">Hotspot: <b>{hotspot}</b></div>
        </div>

        <div className="smallCard">
          <div className="mutedSmall">Top Drivers</div>
          <ol className="drivers">
            {drivers.map((d, i) => <li key={i}>{d}</li>)}
          </ol>
        </div>
      </div>

      <div className="dashPlaceholder">
        Charts placeholder: risk trend, defects by module, metrics over time.
      </div>

      <button className="btn" onClick={refresh} disabled={loading} style={{ marginTop: 12 }}>
        {loading ? "Refreshing..." : "Refresh Dashboard"}
      </button>
    </div>
  );
}