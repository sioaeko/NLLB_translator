import type { ApiKeys, Engine, Language, TranslateResponse } from "./types";

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

function translationHeaders(keys: ApiKeys): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (keys.gemini) headers["X-Gemini-Key"] = keys.gemini;
  if (keys.groq) headers["X-Groq-Key"] = keys.groq;
  if (keys.openai) headers["X-OpenAI-Key"] = keys.openai;
  if (keys.openrouter) headers["X-OpenRouter-Key"] = keys.openrouter;
  if (keys.openrouter_model) headers["X-OpenRouter-Model"] = keys.openrouter_model;
  return headers;
}

async function checkResponse(res: Response) {
  if (res.ok) return;
  const detail = await res.json().then((data) => data.detail).catch(() => null);
  throw new Error(typeof detail === "string" ? detail : `Translation failed (${res.status})`);
}

export async function translate(
  text: string,
  source: string,
  target: string,
  engine: string,
  keys: ApiKeys = {},
  signal?: AbortSignal
): Promise<TranslateResponse> {
  const res = await fetch(`${API_BASE}/api/translate`, {
    method: "POST",
    headers: translationHeaders(keys),
    body: JSON.stringify({ text, source, target, engine }),
    signal,
  });
  await checkResponse(res);
  return (await res.json()) as TranslateResponse;
}

/** Display generated text as it arrives; only a done event marks a complete result. */
export async function translateStream(
  text: string,
  source: string,
  target: string,
  engine: string,
  keys: ApiKeys,
  onDelta: (text: string) => void,
  signal?: AbortSignal
): Promise<TranslateResponse> {
  const res = await fetch(`${API_BASE}/api/translate/stream`, {
    method: "POST",
    headers: translationHeaders(keys),
    body: JSON.stringify({ text, source, target, engine }),
    signal,
  });
  // Support older deployments without retrying failed inference or billable requests.
  if (res.status === 404 || res.status === 405) {
    await res.body?.cancel();
    return translate(text, source, target, engine, keys, signal);
  }
  await checkResponse(res);
  if (!res.body) throw new Error("The translation response was empty. Please try again.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function readEvent(line: string): TranslateResponse | undefined {
    signal?.throwIfAborted();
    if (!line.trim()) return;
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      throw new Error("The translation response was invalid. Please try again.");
    }
    if (event?.type === "delta" && typeof event.text === "string") {
      if (event.text) onDelta(event.text);
      return;
    }
    if (event?.type === "done" && typeof event.translation === "string" &&
        typeof event.source === "string" && typeof event.target === "string" &&
        typeof event.engine === "string") {
      return { translation: event.translation, source: event.source, target: event.target, engine: event.engine };
    }
    if (event?.type === "error") {
      throw new Error(typeof event.detail === "string" ? event.detail : "Translation failed. Please try again.");
    }
    throw new Error("The translation response was invalid. Please try again.");
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      signal?.throwIfAborted();
      buffer += decoder.decode(value, { stream: !done });
      let newline;
      while ((newline = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newline);
        buffer = buffer.slice(newline + 1);
        const result = readEvent(line);
        if (result) return result;
      }
      if (done) {
        const result = readEvent(buffer);
        if (result) return result;
        throw new Error("Translation was interrupted before it finished. Please try again.");
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
