import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

export default function UploadPage({ selectedProjectId, onSelectProject }) {
  const [projectId, setProjectId] = useState(selectedProjectId || "");
  const [file, setFile] = useState(null);
  const [ok, setOk] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  // New: store response from backend so we can render it
  const [prediction, setPrediction] = useState(null);

  useEffect(() => {
    setProjectId(selectedProjectId || "");
  }, [selectedProjectId]);

  const summary = prediction?.summary;
  const results = Array.isArray(prediction?.results) ? prediction.results : [];

  const previewRows = useMemo(() => {
    return results.slice(0, 20);
  }, [results]);

  function downloadJson() {
    if (!prediction) return;
    const blob = new Blob([JSON.stringify(prediction, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prediction_${prediction.project_id || "project"}_${prediction.run_id || "run"}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function upload() {
    setOk("");
    setErr("");
    setPrediction(null);

    const pid = projectId.trim();
    if (!pid) return setErr("Project ID is required.");
    if (!file) return setErr("Please choose a CSV file.");

    setLoading(true);
    try {
      const data = await api.uploadCsv(pid, file); // <-- captures backend result
      onSelectProject(pid); // keep global selection
      setPrediction(data);  // <-- display it
      setOk(`Uploaded & predicted ✅ (rows: ${data?.rows ?? "?"})`);
    } catch (e) {
      setErr(e.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="title">Upload CSV</div>
      <p className="sub">
        Endpoint used: <b>POST /projects/{`{project_id}`}/predict_csv</b>
      </p>

      {ok && <div className="notice ok">{ok}</div>}
      {err && <div className="notice bad">{err}</div>}

      <div className="panel inner" style={{ maxWidth: 900 }}>
        <label className="label">Project ID</label>
        <input
          className="input"
          value={projectId}
          placeholder="e.g., 1"
          onChange={(e) => setProjectId(e.target.value)}
        />

        <label className="label">CSV File</label>
        <input
          className="inputFile"
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        <div className="row" style={{ gap: 10, marginTop: 10 }}>
          <button className="btn btnPrimary" onClick={upload} disabled={loading}>
            {loading ? "Uploading..." : "Upload & Predict"}
          </button>

          <button className="btn" onClick={downloadJson} disabled={!prediction}>
            Download JSON
          </button>
        </div>
      </div>

      {/* New: render backend output */}
      {prediction && (
        <div className="panel inner" style={{ marginTop: 16 }}>
          <div className="h2">Prediction Summary</div>

          <div className="cardRow" style={{ marginTop: 12 }}>
            <div className="smallCard">
              <div className="mutedSmall">Run ID</div>
              <div className="mono" style={{ wordBreak: "break-all" }}>
                {prediction.run_id || "-"}
              </div>
              <div className="muted">Rows: <b>{prediction.rows ?? results.length}</b></div>
            </div>

            <div className="smallCard">
              <div className="mutedSmall">Defective Count</div>
              <div className="bigNum">{summary?.count_defective ?? "-"}</div>
              <div className="muted">
                Percent defective: <b>{summary?.percent_defective != null ? `${Number(summary.percent_defective).toFixed(2)}%` : "-"}</b>
              </div>
            </div>

            <div className="smallCard">
              <div className="mutedSmall">Avg Defect Probability</div>
              <div className="bigNum">
                {summary?.avg_probability_defect != null ? Number(summary.avg_probability_defect).toFixed(3) : "-"}
              </div>
              <div className="muted">
                Buckets — Low: <b>{summary?.risk_buckets?.low ?? "-"}</b>, Medium: <b>{summary?.risk_buckets?.medium ?? "-"}</b>, High: <b>{summary?.risk_buckets?.high ?? "-"}</b>
              </div>
            </div>
          </div>

          <div className="h2" style={{ marginTop: 18 }}>Results Preview (first 20 rows)</div>
          <div className="hint">Showing model outputs: probability_defect, predicted_class, risk_level</div>

          <div className="table" style={{ marginTop: 10 }}>
            <div className="th">
              <div>#</div>
              <div>probability_defect</div>
              <div>predicted_class</div>
              <div>risk_level</div>
            </div>

            {previewRows.map((r, idx) => (
              <div className="tr" key={idx}>
                <div className="mono">{idx}</div>
                <div className="mono">
                  {r?.probability_defect != null ? Number(r.probability_defect).toFixed(4) : "-"}
                </div>
                <div className="mono">{r?.predicted_class ?? "-"}</div>
                <div className="strong">{r?.risk_level ?? "-"}</div>
              </div>
            ))}
          </div>

          {results.length > 20 && (
            <div className="muted" style={{ marginTop: 8 }}>
              Showing 20 of {results.length} rows. (Download JSON for the full output.)
            </div>
          )}
        </div>
      )}
    </div>
  );
}