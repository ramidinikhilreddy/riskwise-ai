import { useState } from "react";

export default function UploadPage() {
  const [projectId, setProjectId] = useState("");
  const [file, setFile] = useState(null);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{
        background: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.10)",
        borderRadius: 18,
        padding: 16
      }}>
        <h2 style={{ margin: 0 }}>Upload CSV</h2>
        <p style={{ opacity: 0.75, marginTop: 6 }}>
          Prepare for: <b>POST /projects/{`{project_id}`}/upload</b>
        </p>

        <div style={{ display: "grid", gap: 10, maxWidth: 520 }}>
          <label style={{ fontSize: 13, opacity: 0.8 }}>Project ID</label>
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            placeholder="e.g., 1"
            style={{
              height: 42, borderRadius: 14, padding: "0 12px",
              background: "rgba(0,0,0,0.22)", color: "white",
              border: "1px solid rgba(255,255,255,0.12)"
            }}
          />

          <label style={{ fontSize: 13, opacity: 0.8 }}>CSV File</label>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            style={{ color: "white" }}
          />

          <button
            disabled={!projectId || !file}
            onClick={() => alert("Upload endpoint not connected yet. UI ready.")}
            style={{
              height: 42,
              borderRadius: 14,
              fontWeight: 900,
              cursor: "pointer",
              border: "1px solid rgba(255,255,255,0.14)",
              background: "linear-gradient(135deg, rgba(124,58,237,1), rgba(6,182,212,0.95))",
              color: "white",
              opacity: (!projectId || !file) ? 0.5 : 1
            }}
          >
            Upload (soon)
          </button>
        </div>
      </div>
    </div>
  );
}