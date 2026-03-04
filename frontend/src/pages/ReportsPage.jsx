export default function ReportsPage() {
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{
        background: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.10)",
        borderRadius: 18,
        padding: 16
      }}>
        <h2 style={{ margin: 0 }}>Reports</h2>
        <p style={{ opacity: 0.75, marginTop: 6 }}>
          UI ready for export endpoints (PDF/HTML).
        </p>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10 }}>
          <button
            onClick={() => alert("Connect later: /projects/{id}/report.pdf")}
            style={{
              height: 42,
              borderRadius: 14,
              fontWeight: 900,
              cursor: "pointer",
              border: "1px solid rgba(255,255,255,0.14)",
              background: "linear-gradient(135deg, rgba(124,58,237,1), rgba(6,182,212,0.95))",
              color: "white",
              padding: "0 14px"
            }}
          >
            Export PDF (soon)
          </button>

          <button
            onClick={() => alert("Connect later: /projects/{id}/report.html")}
            style={{
              height: 42,
              borderRadius: 14,
              fontWeight: 900,
              cursor: "pointer",
              border: "1px solid rgba(255,255,255,0.12)",
              background: "rgba(255,255,255,0.06)",
              color: "white",
              padding: "0 14px"
            }}
          >
            Export HTML (soon)
          </button>
        </div>
      </div>
    </div>
  );
}