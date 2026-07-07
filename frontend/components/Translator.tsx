"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import LanguageSelect from "./LanguageSelect";
import EngineSelect from "./EngineSelect";
import Settings from "./Settings";
import { fetchEngines, fetchLanguages, translate } from "@/lib/api";
import { loadKeys, saveKeys } from "@/lib/keys";
import type { ApiKeys, Engine, Language } from "@/lib/types";

const MAX_CHARS = 5000;
const DEBOUNCE_MS = 500;

export default function Translator() {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [engine, setEngine] = useState("");
  const [source, setSource] = useState("eng_Latn");
  const [target, setTarget] = useState("kor_Hang");
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [copied, setCopied] = useState(false);
  const [keys, setKeys] = useState<ApiKeys>({});
  const [settingsOpen, setSettingsOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setKeys(loadKeys());
    Promise.all([fetchLanguages(), fetchEngines()])
      .then(([langs, eng]) => {
        setLanguages(langs);
        setEngines(eng.engines);
        setEngine(eng.default ?? "");
        setOffline(false);
      })
      .catch(() => setOffline(true));
  }, []);

  // An API engine is usable if the server has a key OR the user stored one here.
  const augmentedEngines = useMemo(
    () =>
      engines.map((e) => ({
        ...e,
        available: e.available || (!!e.key_field && !!keys[e.key_field]),
      })),
    [engines, keys]
  );

  const runTranslate = useCallback(
    async (text: string, src: string, tgt: string, eng: string, k: ApiKeys) => {
      abortRef.current?.abort();
      if (!text.trim() || !eng) {
        setOutput("");
        setLoading(false);
        return;
      }
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      setError(null);
      try {
        const res = await translate(text, src, tgt, eng, k, controller.signal);
        setOutput(res.translation);
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setError((e as Error).message);
          setOutput("");
        }
      } finally {
        if (abortRef.current === controller) setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    const id = setTimeout(() => runTranslate(input, source, target, engine, keys), DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [input, source, target, engine, keys, runTranslate]);

  function swap() {
    setSource(target);
    setTarget(source);
    setInput(output);
    setOutput(input);
  }

  async function copyOutput() {
    if (!output) return;
    await navigator.clipboard.writeText(output);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function handleSaveKeys(next: ApiKeys) {
    saveKeys(next);
    setKeys(loadKeys());
    setSettingsOpen(false);
  }

  const activeEngine = augmentedEngines.find((e) => e.id === engine);
  const noEngine = !offline && engines.length > 0 && !engine;

  return (
    <div className="mx-auto w-full max-w-4xl">
      <div className="relative rounded-2xl border border-slate-200/80 bg-white shadow-xl shadow-slate-900/5 ring-1 ring-black/[0.02] dark:border-slate-800 dark:bg-slate-900 dark:shadow-black/20">
        {/* top loading bar */}
        <div
          className={`pointer-events-none absolute inset-x-0 top-0 h-0.5 overflow-hidden rounded-t-2xl ${loading ? "opacity-100" : "opacity-0"} transition-opacity`}
        >
          <div className="h-full w-1/3 animate-[loading_1.1s_ease-in-out_infinite] bg-gradient-to-r from-indigo-500 to-violet-500" />
        </div>

        {/* Toolbar: engine + settings */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
          <EngineSelect engines={augmentedEngines} value={engine} onChange={setEngine} />
          <div className="flex items-center gap-2">
            {activeEngine && (
              <span className="hidden text-xs text-slate-400 sm:inline">
                {activeEngine.private
                  ? "🔒 Runs locally · text stays on device"
                  : "☁ Sent to provider’s free API"}
              </span>
            )}
            <button
              onClick={() => setSettingsOpen(true)}
              aria-label="API key settings"
              className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Language bar */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 border-b border-slate-100 px-3 py-2 dark:border-slate-800">
          <div className="justify-self-start">
            <LanguageSelect languages={languages} value={source} onChange={setSource} label="Source language" />
          </div>
          <button
            onClick={swap}
            aria-label="Swap languages"
            className="rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-indigo-600 dark:hover:bg-slate-800"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M7 16V4m0 0L3 8m4-4l4 4M17 8v12m0 0l4-4m-4 4l-4-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <div className="justify-self-end">
            <LanguageSelect languages={languages} value={target} onChange={setTarget} label="Target language" align="right" />
          </div>
        </div>

        {/* Panes */}
        <div className="grid divide-y divide-slate-100 overflow-hidden rounded-b-2xl md:grid-cols-2 md:divide-x md:divide-y-0 dark:divide-slate-800">
          {/* Input */}
          <div className="flex flex-col">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, MAX_CHARS))}
              placeholder="Enter text…"
              className="h-56 w-full resize-none bg-transparent p-4 text-lg leading-relaxed outline-none placeholder:text-slate-300 dark:placeholder:text-slate-600"
            />
            <div className="flex items-center justify-between px-4 py-2.5 text-xs text-slate-400">
              <button
                onClick={() => setInput("")}
                className={`rounded px-1.5 py-0.5 transition hover:text-slate-600 dark:hover:text-slate-200 ${input ? "" : "invisible"}`}
              >
                Clear
              </button>
              <span className={input.length > MAX_CHARS * 0.9 ? "text-amber-500" : ""}>
                {input.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Output */}
          <div className="flex flex-col bg-slate-50/60 dark:bg-slate-950/30">
            <div className="h-56 w-full overflow-y-auto p-4 text-lg leading-relaxed">
              {noEngine ? (
                <p className="text-sm text-slate-400">
                  No engine ready. Convert a local model, or add a Gemini / Groq key in
                  Settings (⚙) to unlock the cloud engines.
                </p>
              ) : output ? (
                <span className="whitespace-pre-wrap">{output}</span>
              ) : (
                <span className="text-slate-300 dark:text-slate-600">
                  {loading ? "Translating…" : "Translation"}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between px-4 py-2.5 text-xs text-slate-400">
              <span>{activeEngine && output ? `via ${activeEngine.name}` : ""}</span>
              <button
                onClick={copyOutput}
                className={`rounded px-1.5 py-0.5 transition hover:text-slate-600 dark:hover:text-slate-200 ${output ? "" : "invisible"}`}
              >
                {copied ? "✓ Copied" : "Copy"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {offline && (
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-400">
          Can’t reach the translation server. Start the backend (<code className="font-mono">uvicorn main:app</code>) and reload.
        </p>
      )}
      {error && (
        <p className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-950/30 dark:text-red-400">
          {error}
        </p>
      )}

      <Settings
        open={settingsOpen}
        keys={keys}
        onClose={() => setSettingsOpen(false)}
        onSave={handleSaveKeys}
      />
    </div>
  );
}
