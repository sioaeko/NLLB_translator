import type { ApiKeys } from "./types";

const STORAGE_KEY = "nllb_api_keys";

// API keys live only in the browser's localStorage and are sent per-request as
// headers to the backend — never persisted server-side.
export function loadKeys(): ApiKeys {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function saveKeys(keys: ApiKeys): void {
  const clean: ApiKeys = {};
  for (const [k, v] of Object.entries(keys)) {
    if (v && v.trim()) clean[k] = v.trim();
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(clean));
}
