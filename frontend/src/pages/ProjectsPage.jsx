import { useEffect, useState } from "react";
import { api } from "../api";
import { getSelectedProjectId } from "../storage";

export default function ProjectsPage({ onSelectProject }) {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [ok, setOk] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    setOk("");
    setLoading(true);
    try {
      const data = await api.listProjects();
      setProjects(Array.isArray(data) ? data : data.items || []);
    } catch (e) {
      setErr(e.message || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function create() {
    setOk("");
    setErr("");
    if (!name.trim()) return setErr("Project name is required.");

    try {
      await api.createProject({ name: name.trim(), description: description.trim() });
      setName("");
      setDescription("");
      setOk("Project created ✅");
      await load();
    } catch (e) {
      setErr(e.message || "Create failed");
    }
  }

  async function del(id) {
    setOk("");
    setErr("");
    try {
      await api.deleteProject(id);
      setOk("Project deleted ✅");
      await load();
      if (getSelectedProjectId() === id) onSelectProject("");
    } catch (e) {
      setErr(e.message || "Delete failed");
    }
  }

  function select(id) {
    onSelectProject(id);
    setOk("Project selected ✅");
    setErr("");
  }

  return (
    <div className="panel">
      <div className="title">Projects</div>
      <p className="sub">
        Create, select, and manage projects. Selected project ID is used for Upload/Dashboard/Reports.
      </p>

      <div className="members">
        <div className="membersTitle">Group 5 Members</div>
        <ul>
          <li>Nikhil Reddy Ramidi</li>
          <li>Prakriti Shakya</li>
          <li>Mahdi Talebiroveshti</li>
        </ul>
      </div>

      {ok && <div className="notice ok">{ok}</div>}
      {err && <div className="notice bad">{err}</div>}

      <div className="grid2" style={{ marginTop: 16 }}>
        <div className="panel inner">
          <div className="h2">Create Project</div>
          <div className="hint">POST /projects</div>

          <label className="label">Name</label>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Project name" />

          <label className="label">Description</label>
          <input className="input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description (optional)" />

          <button className="btn btnPrimary" onClick={create}>Create</button>
        </div>

        <div className="panel inner">
          <div className="row">
            <div>
              <div className="h2">Projects</div>
              <div className="hint">GET /projects (Select / Delete)</div>
            </div>
            <button className="btn" onClick={load} disabled={loading}>
              {loading ? "Loading..." : "Reload"}
            </button>
          </div>

          <div className="table">
            <div className="th">
              <div>ID</div>
              <div>Name</div>
              <div>Description</div>
              <div style={{ textAlign: "right" }}>Actions</div>
            </div>

            {projects.map((p) => (
              <div className="tr" key={p.id}>
                <div className="mono">{p.id}</div>
                <div className="strong">{p.name}</div>
                <div className="muted">{p.description || "-"}</div>
                <div className="actions">
                  <button className="btn" onClick={() => select(p.id)}>Select</button>
                  <button className="btn danger" onClick={() => del(p.id)}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}