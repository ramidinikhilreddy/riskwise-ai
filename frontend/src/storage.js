const KEY_PROJECT = "riskwise:selectedProjectId";
const KEY_BACKEND_ENABLED = "riskwise:backendEnabled";

export function getSelectedProjectId() {
  return localStorage.getItem(KEY_PROJECT) || "";
}

export function setSelectedProjectId(id) {
  if (!id) localStorage.removeItem(KEY_PROJECT);
  else localStorage.setItem(KEY_PROJECT, id);
}

export function getBackendEnabled() {
  const v = localStorage.getItem(KEY_BACKEND_ENABLED);
  return v === null ? true : v === "true";
}

export function setBackendEnabled(enabled) {
  localStorage.setItem(KEY_BACKEND_ENABLED, String(Boolean(enabled)));
}