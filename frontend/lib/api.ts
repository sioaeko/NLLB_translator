import type { Engine, Language, TranslateResponse } from "./types";

// Same-origin by default (single-container deploy); override for split dev/prod.
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000";

export async function fetchLanguages(): Promise<Language[]> {
  const res = await fetch(`${API_BASE}/api/languages`);
  if (!res.ok) throw new Error("Failed to load languages");
  const data = await res.json();
  return data.languages as Language[];
}

export async function fetchEngines(): Promise<{ engines: Engine[]; default: string | null }> {
  const res = await fetch(`${API_BASE}/api/engines`);
  if (!res.ok) throw new Error("Failed to load engines");
  return res.json();
}

export async function translate(
  text: string,
  source: string,
  target: string,
  engine: string,
  signal?: AbortSignal
): Promise<TranslateResponse> {
  const res = await fetch(`${API_BASE}/api/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source, target, engine }),
    signal,
  });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d) => d.detail)
      .catch(() => null);
    throw new Error(detail || `Translation failed (${res.status})`);
  }
  return (await res.json()) as TranslateResponse;
}
