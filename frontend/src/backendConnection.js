const KEY = "riskwise:backendEnabled";

export function isBackendEnabled() {
  const v = localStorage.getItem(KEY);
  return v === null ? true : v === "true"; // default ON
}

export function setBackendEnabled(enabled) {
  localStorage.setItem(KEY, String(!!enabled));
}