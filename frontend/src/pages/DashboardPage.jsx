export default function DashboardPage() {
  const riskScore = 0.74;
  const riskLevel = riskScore > 0.7 ? "High" : riskScore > 0.4 ? "Medium" : "Low";

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{
        background: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.10)",
        borderRadius: 18,
        padding: 16
      }}>
        <h2 style={{ margin: 0 }}>Dashboard</h2>
        <p style={{ opacity: 0.75, marginTop: 6 }}>
          Mock preview (replace with API later)
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
          <div style={{ padding: 14, borderRadius: 16, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.05)" }}>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Risk Score</div>
            <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>{riskScore.toFixed(2)}</div>
            <div style={{ marginTop: 8, opacity: 0.85 }}>Level: <b>{riskLevel}</b></div>
          </div>

          <div style={{ padding: 14, borderRadius: 16, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.05)" }}>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Predicted Defects</div>
            <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>12</div>
            <div style={{ marginTop: 8, opacity: 0.85 }}>Hotspot: <b>auth.py</b></div>
          </div>

          <div style={{ padding: 14, borderRadius: 16, border: "1px solid rgba(255,255,255,0.10)", background: "rgba(255,255,255,0.05)" }}>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Top Drivers</div>
            <ol style={{ marginTop: 10, opacity: 0.85 }}>
              <li>High churn</li>
              <li>Low test coverage</li>
              <li>Large commits</li>
            </ol>
          </div>
        </div>

        <div style={{ marginTop: 12, padding: 14, borderRadius: 16, border: "1px dashed rgba(255,255,255,0.18)", opacity: 0.8 }}>
          Charts placeholder: risk trend, defects by module, metrics over time.
        </div>
      </div>
    </div>
  );
}