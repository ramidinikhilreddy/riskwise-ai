import { getBackendEnabled } from "./storage";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

export const api = {
  baseUrl: BASE_URL,

  health: () => request("/health"),

  listProjects: () => request("/projects"),
  createProject: (payload) =>
    request("/projects", { method: "POST", body: JSON.stringify(payload) }),
  deleteProject: (projectId) =>
    request(`/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" }),

  uploadCsv: (projectId, file) => {
    const form = new FormData();
    form.append("file", file);

    return fetch(`${BASE_URL}/projects/${encodeURIComponent(projectId)}/upload`, {
      method: "POST",
      body: form,
    }).then(async (res) => {
      if (!getBackendEnabled()) throw new Error("Backend disconnected (disabled in UI).");
      if (!res.ok) throw new Error((await res.text()) || `Upload failed: ${res.status}`);
      return res.json().catch(() => ({}));
    });
  },

  // Dashboard: try multiple endpoints so it works even if your backend differs
  getDashboard: async (projectId) => {
    const candidates = [
      `/projects/${encodeURIComponent(projectId)}/dashboard`,
      `/projects/${encodeURIComponent(projectId)}/summary`,
      `/dashboard/${encodeURIComponent(projectId)}`,
      `/dashboard?project_id=${encodeURIComponent(projectId)}`,
    ];

    let lastErr = null;
    for (const path of candidates) {
      try {
        return await request(path);
      } catch (e) {
        lastErr = e;
      }
    }
    throw lastErr || new Error("Dashboard endpoint not found");
  },
};