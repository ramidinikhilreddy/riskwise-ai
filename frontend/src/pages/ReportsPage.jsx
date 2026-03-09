import { useState } from "react";
import { api } from "../api";

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export default function ReportsPage({ selectedProjectId }) {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  // Model evaluation
  const [evalFile, setEvalFile] = useState(null);
  const [labelCol, setLabelCol] = useState("defect");
  const [evalBusy, setEvalBusy] = useState(false);
  const [evalRes, setEvalRes] = useState(null);

  async function exportPdf() {
    setErr("");
    setMsg("");
    if (!selectedProjectId) return setErr("No project selected. Go to Projects and click Select.");
    setLoading(true);
    try {
      const blob = await api.exportReportPdf(selectedProjectId);
      downloadBlob(blob, `riskwise_report_${selectedProjectId}.pdf`);
      setMsg("PDF downloaded ✅");
    } catch (e) {
      setErr(e?.message || "Failed to export PDF");
    } finally {
      setLoading(false);
    }
  }

  async function exportHtml() {
    setErr("");
    setMsg("");
    if (!selectedProjectId) return setErr("No project selected. Go to Projects and click Select.");
    setLoading(true);
    try {
      const blob = await api.exportReportHtml(selectedProjectId);
      downloadBlob(blob, `riskwise_report_${selectedProjectId}.html`);
      setMsg("HTML downloaded ✅");
    } catch (e) {
      setErr(e?.message || "Failed to export HTML");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="title">Reports</div>
      <p className="sub">
        Export a report from the latest prediction run for the selected project.
      </p>

      {err && <div className="notice bad">{err}</div>}
      {msg && <div className="notice ok">{msg}</div>}

      <div className="panel inner" style={{ maxWidth: 700 }}>
        <div className="row">
          <button className="btn btnPrimary" onClick={exportPdf} disabled={loading}>
            {loading ? "Working..." : "Export PDF"}
          </button>
          <button className="btn" onClick={exportHtml} disabled={loading}>
            {loading ? "Working..." : "Export HTML"}
          </button>
        </div>
        <p className="sub" style={{ marginTop: 10 }}>
          Tip: If you get “No prediction runs yet”, go to Upload and upload a CSV first.
        </p>
      </div>

      <div className="panel inner" style={{ maxWidth: 900, marginTop: 14 }}>
        <div className="title" style={{ fontSize: 18, marginBottom: 6 }}>Model Evaluation</div>
        <p className="sub">
          Upload a <b>labeled</b> CSV to compute accuracy / precision / recall / F1.
          The CSV must include all required feature columns plus the label column.
        </p>

        <div className="row" style={{ gap: 10, alignItems: "end" }}>
          <div style={{ flex: 1 }}>
            <div className="mutedSmall">Label column name</div>
            <input
              className="input"
              value={labelCol}
              onChange={(e) => setLabelCol(e.target.value)}
              placeholder="defect"
            />
          </div>
          <div style={{ flex: 2 }}>
            <div className="mutedSmall">Labeled CSV file</div>
            <input
              className="input"
              type="file"
              accept=".csv"
              onChange={(e) => setEvalFile(e.target.files?.[0] || null)}
            />
          </div>
          <button
            className="btn btnPrimary"
            disabled={evalBusy || !selectedProjectId || !evalFile}
            onClick={async () => {
              setErr("");
              setMsg("");
              setEvalRes(null);
              if (!selectedProjectId) return setErr("No project selected. Go to Projects and click Select.");
              if (!evalFile) return setErr("Choose a labeled CSV file first.");
              setEvalBusy(true);
              try {
                const r = await api.evaluateCsv(selectedProjectId, evalFile, labelCol || "defect");
                setEvalRes(r);
                setMsg("Evaluation computed ✅ (also added to reports/dashboard)");
              } catch (e) {
                setErr(e?.message || "Failed to evaluate model");
              } finally {
                setEvalBusy(false);
              }
            }}
          >
            {evalBusy ? "Working..." : "Run Evaluation"}
          </button>
        </div>

        {evalRes ? (
          <div className="panel inner" style={{ marginTop: 12 }}>
            <div className="cardRow">
              <div className="smallCard"><div className="mutedSmall">Accuracy</div><div className="bigNum">{Number(evalRes.accuracy).toFixed(3)}</div></div>
              <div className="smallCard"><div className="mutedSmall">Precision</div><div className="bigNum">{Number(evalRes.precision).toFixed(3)}</div></div>
              <div className="smallCard"><div className="mutedSmall">Recall</div><div className="bigNum">{Number(evalRes.recall).toFixed(3)}</div></div>
              <div className="smallCard"><div className="mutedSmall">F1</div><div className="bigNum">{Number(evalRes.f1).toFixed(3)}</div></div>
            </div>
            <div className="muted" style={{ marginTop: 10 }}>
              Confusion matrix (rows=true, cols=pred):
              <div className="mono" style={{ marginTop: 6, whiteSpace: "pre-wrap" }}>{JSON.stringify(evalRes.confusion_matrix)}</div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}