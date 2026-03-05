import { useState } from "react";
import { api } from "../api";

export default function UploadPage({ selectedProjectId, onSelectProject }) {
  const [projectId, setProjectId] = useState(selectedProjectId || "");
  const [file, setFile] = useState(null);
  const [ok, setOk] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function upload() {
    setOk("");
    setErr("");

    const pid = projectId.trim();
    if (!pid) return setErr("Project ID is required.");
    if (!file) return setErr("Please choose a CSV file.");

    setLoading(true);
    try {
      await api.uploadCsv(pid, file);
      onSelectProject(pid); // ✅ save to global selected
      setOk("CSV uploaded ✅");
    } catch (e) {
      setErr(e.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="title">Upload CSV</div>
      <p className="sub">Prepare for: <b>POST /projects/{`{project_id}`}/upload</b></p>

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

        <button className="btn btnPrimary" onClick={upload} disabled={loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </div>
    </div>
  );
}