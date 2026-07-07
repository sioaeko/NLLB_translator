"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import LanguageSelect from "./LanguageSelect";
import EngineSelect from "./EngineSelect";
import { fetchEngines, fetchLanguages, translate } from "@/lib/api";
import type { Engine, Language } from "@/lib/types";

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

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    Promise.all([fetchLanguages(), fetchEngines()])
      .then(([langs, eng]) => {
        setLanguages(langs);
        setEngines(eng.engines);
        setEngine(eng.default ?? "");
        setOffline(false);
      })
      .catch(() => setOffline(true));
  }, []);

  const runTranslate = useCallback(
    async (text: string, src: string, tgt: string, eng: string) => {
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
        const res = await translate(text, src, tgt, eng, controller.signal);
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
    const id = setTimeout(() => runTranslate(input, source, target, engine), DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [input, source, target, engine, runTranslate]);

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

  const activeEngine = engines.find((e) => e.id === engine);
  const noEngine = !offline && engines.length > 0 && !engine;

  return (
    <div className="mx-auto w-full max-w-4xl">
      <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-xl shadow-slate-900/5 ring-1 ring-black/[0.02] dark:border-slate-800 dark:bg-slate-900 dark:shadow-black/20">
        {/* top loading bar */}
        <div
          className={`absolute inset-x-0 top-0 h-0.5 overflow-hidden ${loading ? "opacity-100" : "opacity-0"} transition-opacity`}
        >
          <div className="h-full w-1/3 animate-[loading_1.1s_ease-in-out_infinite] bg-gradient-to-r from-indigo-500 to-violet-500" />
        </div>

        {/* Toolbar: engine */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
          <EngineSelect engines={engines} value={engine} onChange={setEngine} />
          {activeEngine && (
            <span className="text-xs text-slate-400">
              {activeEngine.private
                ? "🔒 Runs locally · text stays on device"
                : "☁ Sent to provider’s free API"}
            </span>
          )}
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
        <div className="grid divide-y divide-slate-100 md:grid-cols-2 md:divide-x md:divide-y-0 dark:divide-slate-800">
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
                  No engine configured yet. Convert the NLLB model, or add a Gemini/Groq API key, then reload.
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
    </div>
  );
}
