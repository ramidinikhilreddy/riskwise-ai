import { getBackendEnabled } from "./storage";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

/**
 * JSON request helper (use ONLY for JSON endpoints).
 * Do NOT use this for file uploads (FormData).
 */
async function request(path, options = {}) {
  if (!getBackendEnabled()) {
    throw new Error("Backend disconnected (disabled in UI).");
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed: ${res.status}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

/**
 * Helper to store last prediction so Dashboard can show it.
 */
function storeLastPrediction(projectId, data) {
  try {
    localStorage.setItem("riskwise:lastPrediction", JSON.stringify(data));
    if (projectId) {
      localStorage.setItem(`riskwise:lastPrediction:${projectId}`, JSON.stringify(data));
    }
  } catch {
    // ignore storage errors
  }
}

export const api = {
  baseUrl: BASE_URL,

  // Health
  health: () => request("/health"),

  // Projects (note trailing slash to avoid 307 redirect)
  listProjects: () => request("/projects/"),
  createProject: (payload) =>
    request("/projects/", { method: "POST", body: JSON.stringify(payload) }),
  deleteProject: (projectId) =>
    request(`/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" }),

  /**
   * Upload CSV and get predictions
   * Backend endpoint: POST /projects/{project_id}/predict_csv
   */
  uploadCsv: async (projectId, file) => {
    if (!getBackendEnabled()) {
      throw new Error("Backend disconnected (disabled in UI).");
    }
    if (!projectId) throw new Error("Missing projectId");
    if (!file) throw new Error("No file selected");

    const form = new FormData();
    form.append("file", file);

    const res = await fetch(
      `${BASE_URL}/projects/${encodeURIComponent(projectId)}/predict_csv`,
      {
        method: "POST",
        body: form,
        // IMPORTANT: do NOT set Content-Type for FormData; browser sets boundary
      }
    );

    if (!res.ok) {
      throw new Error((await res.text().catch(() => "")) || `Upload failed: ${res.status}`);
    }

    const data = await res.json().catch(() => ({}));

    // Save for dashboard use
    storeLastPrediction(projectId, data);

    return data;
  },

  /**
   * Predict single module from JSON
   * Backend endpoint: POST /projects/{project_id}/predict_single
   * Body: { features: { ... } }
   */
  predictSingle: (projectId, features) => {
    if (!projectId) throw new Error("Missing projectId");
    return request(`/projects/${encodeURIComponent(projectId)}/predict_single`, {
      method: "POST",
      body: JSON.stringify({ features }),
    });
  },

  /**
   * Dashboard (for NOW): use last stored prediction from uploadCsv.
   * This avoids needing a separate backend dashboard endpoint.
   */
  getDashboard: async (projectId) => {
    const key = projectId
      ? `riskwise:lastPrediction:${projectId}`
      : "riskwise:lastPrediction";
    const raw = localStorage.getItem(key) || localStorage.getItem("riskwise:lastPrediction");
    if (!raw) throw new Error("No prediction found yet. Upload a CSV first.");
    return JSON.parse(raw);
  },
};
