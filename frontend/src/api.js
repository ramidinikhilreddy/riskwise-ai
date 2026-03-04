const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8080";

async function request(path, options = {}) {
  const isForm = options.body instanceof FormData;

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return null;
  return res.json();
}

export function listProjects() {
  return request("/projects", { method: "GET" });
}

export function createProject(data) {
  return request("/projects", { method: "POST", body: JSON.stringify(data) });
}

export function updateProject(id, data) {
  return request(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteProject(id) {
  return request(`/projects/${id}`, { method: "DELETE" });
}