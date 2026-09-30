"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import LanguageSelect from "./LanguageSelect";
import EngineSelect from "./EngineSelect";
import EngineIcon from "./EngineIcon";
import Settings from "./Settings";
import { fetchEngines, fetchLanguages, translate } from "@/lib/api";
import { loadKeys, saveKeys } from "@/lib/keys";
import { KEY_FIELDS, OPENROUTER_MODEL_KEY, SENT_TO, openRouterLabel } from "@/lib/engines";
import type { ApiKeys, Engine, Language } from "@/lib/types";

const MAX_CHARS = 5000;
const DEBOUNCE_MS = 500;
const SLOW_MS = 2500;

const SAMPLES = [
  { lang: "eng_Latn", tag: "EN", text: "Where is the nearest subway station?" },
  { lang: "kor_Hang", tag: "KO", text: "오늘 날씨 정말 좋네요." },
  { lang: "jpn_Jpan", tag: "JA", text: "駅までどのくらいかかりますか?" },
  { lang: "spa_Latn", tag: "ES", text: "Me encantaría visitar Seúl algún día." },
];

// FLORES-200 → BCP 47, so browsers pick the right CJK glyphs and hyphenation.
const TWO_LETTER: Record<string, string> = {
  eng: "en", kor: "ko", jpn: "ja", spa: "es", fra: "fr", deu: "de", rus: "ru", por: "pt",
  ita: "it", vie: "vi", tha: "th", hin: "hi", arb: "ar", ind: "id", tur: "tr", pol: "pl",
  nld: "nl", ukr: "uk", heb: "he",
};
function toBcp47(code: string) {
  const [lang, script] = code.split("_");
  if (lang === "zho") return `zh-${script}`;
  return TWO_LETTER[lang] ?? `${lang}-${script}`;
}

const requestKey = (text: string, src: string, tgt: string, eng: string) =>
  JSON.stringify([text, src, tgt, eng]);

const iconProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

const ghostBtn =
  "inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-medium text-slate-600 transition hover:bg-slate-900/[0.05] hover:text-slate-900 active:scale-[0.97] dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-slate-100";

export default function Translator() {
  const [languages, setLanguages] = useState<Language[]>([]);
  const [engines, setEngines] = useState<Engine[]>([]);
  const [engine, setEngine] = useState("");
  const [source, setSource] = useState("eng_Latn");
  const [target, setTarget] = useState("kor_Hang");
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [outputFor, setOutputFor] = useState(""); // request that produced `output`
  const [loading, setLoading] = useState(false);
  const [slow, setSlow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [copied, setCopied] = useState(false);
  const [flip, setFlip] = useState(false);
  const [keys, setKeys] = useState<ApiKeys>({});
  const [settingsOpen, setSettingsOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

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
  // OpenRouter's description reflects the model the user picked.
  const augmentedEngines = useMemo(
    () =>
      engines.map((e) => ({
        ...e,
        available: e.available || (!!e.key_field && !!keys[e.key_field]),
        description:
          e.id === "openrouter" && keys[OPENROUTER_MODEL_KEY]
            ? `Using ${openRouterLabel(keys[OPENROUTER_MODEL_KEY])}`
            : e.description,
      })),
    [engines, keys]
  );

  const runTranslate = useCallback(
    async (text: string, src: string, tgt: string, eng: string, k: ApiKeys) => {
      abortRef.current?.abort();
      if (!text.trim() || !eng) {
        setOutput("");
        setError(null);
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
        setOutputFor(requestKey(text, src, tgt, eng));
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

  // Only surface the "still working" note when a request takes a while.
  useEffect(() => {
    if (!loading) {
      setSlow(false);
      return;
    }
    const id = setTimeout(() => setSlow(true), SLOW_MS);
    return () => clearTimeout(id);
  }, [loading]);

  // Grow the textarea with its content; CSS caps the height.
  const fit = useCallback(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${ta.scrollHeight}px`;
  }, []);
  useLayoutEffect(fit, [input, fit]);
  useEffect(() => {
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [fit]);

  function swap() {
    setFlip((f) => !f);
    setSource(target);
    setTarget(source);
    setInput(output);
    setOutput(input);
  }

  function applySample(s: (typeof SAMPLES)[number]) {
    setSource(s.lang);
    if (target === s.lang) setTarget(s.lang === "kor_Hang" ? "eng_Latn" : "kor_Hang");
    setInput(s.text);
    taRef.current?.focus();
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
  const hasKeys = KEY_FIELDS.some((k) => !!keys[k]);
  // Between an edit and the debounced request, the shown translation belongs to
  // older input: dim it rather than let it pass for the current result.
  const hasInput = !!input.trim();
  const stale = !!output && outputFor !== requestKey(input, source, target, engine);
  const provider = activeEngine ? SENT_TO[activeEngine.key_field] ?? "the provider" : "";
  const usesOwnKey = !!activeEngine?.key_field && !!keys[activeEngine.key_field];

  let result: React.ReactNode;
  if (noEngine) {
    result = (
      <div className="text-[15px] text-slate-600 dark:text-slate-400">
        <p>No engine is ready on this server yet.</p>
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          className="mt-2 font-medium text-accent-600 underline-offset-4 hover:underline dark:text-accent-400"
        >
          Add a cloud API key
        </button>
      </div>
    );
  } else if (error) {
    result = (
      <div className="text-[15px]">
        <p className="flex items-start gap-2 text-red-600 dark:text-red-400">
          <svg className="mt-0.5 h-[18px] w-[18px] shrink-0" {...iconProps}>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v4.5M12 16h.01" />
          </svg>
          <span>{error}</span>
        </p>
        <button
          type="button"
          onClick={() => runTranslate(input, source, target, engine, keys)}
          className="mt-2.5 font-medium text-accent-600 underline-offset-4 hover:underline dark:text-accent-400"
        >
          Try again
        </button>
      </div>
    );
  } else if (hasInput && loading && !output) {
    result = (
      <div>
        <span className="sr-only">Translating</span>
        <div className="space-y-3 pt-1.5" aria-hidden="true">
          <div className="skeleton h-3.5 w-11/12 rounded-full" />
          <div className="skeleton h-3.5 w-3/4 rounded-full" />
          <div className="skeleton h-3.5 w-2/5 rounded-full" />
        </div>
        {slow && (
          <p className="mt-5 text-sm text-slate-500 dark:text-slate-400">
            {activeEngine?.kind === "local"
              ? "Warming up the model. The first translation can take around 10 seconds."
              : `Waiting for ${provider}…`}
          </p>
        )}
      </div>
    );
  } else if (hasInput && output) {
    result = (
      <p
        lang={toBcp47(target)}
        dir="auto"
        data-stale={stale || loading}
        className={`whitespace-pre-wrap transition-opacity duration-200 ${stale || loading ? "opacity-45" : ""}`}
      >
        {output}
      </p>
    );
  } else {
    result = <p className="text-slate-400 dark:text-slate-500">Translation</p>;
  }

  return (
    <div className="w-full">
      <section
        aria-label="Translator"
        className="relative rounded-2xl border border-slate-900/[0.08] bg-white shadow-[0_1px_2px_rgb(15_23_42/0.04),0_16px_40px_-22px_rgb(15_23_42/0.22)] transition-[border-color] duration-200 focus-within:border-accent-300 dark:border-white/[0.08] dark:bg-surface-dark dark:shadow-[0_16px_40px_-22px_rgb(0_0_0/0.9)] dark:focus-within:border-accent-800"
      >
        {/* top progress bar */}
        <div
          className={`pointer-events-none absolute inset-x-0 top-0 h-0.5 overflow-hidden rounded-t-2xl transition-opacity ${loading ? "opacity-100" : "opacity-0"}`}
        >
          <div className="h-full w-1/3 animate-loading bg-accent-500" />
        </div>

        {/* Toolbar: engine · where text goes · keys */}
        <div className="flex items-center justify-between gap-2 border-b border-slate-900/[0.06] p-1.5 pr-2 dark:border-white/[0.06]">
          <EngineSelect
            engines={augmentedEngines}
            value={engine}
            onChange={setEngine}
            onRequestKey={() => setSettingsOpen(true)}
            loading={engines.length === 0 && !offline}
          />
          <div className="flex items-center gap-1">
            {activeEngine && (
              <span className="mr-1 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                {activeEngine.kind === "local" ? (
                  <svg className="h-3.5 w-3.5" {...iconProps}>
                    <rect x="3" y="4" width="18" height="7" rx="2" />
                    <rect x="3" y="13" width="18" height="7" rx="2" />
                    <path d="M7 7.5h.01M7 16.5h.01" />
                  </svg>
                ) : (
                  <svg className="h-3.5 w-3.5" {...iconProps}>
                    <path d="M2.25 15a4.5 4.5 0 0 0 4.5 4.5H18a3.75 3.75 0 0 0 1.332-7.257 3 3 0 0 0-3.758-3.848 5.25 5.25 0 0 0-10.233 2.33A4.502 4.502 0 0 0 2.25 15Z" />
                  </svg>
                )}
                <span className="sm:hidden">{activeEngine.kind === "local" ? "This server" : `Via ${provider}`}</span>
                <span className="hidden sm:inline">
                  {activeEngine.kind === "local"
                    ? "Runs on this server · no third-party API"
                    : `Sent to ${provider}${usesOwnKey ? " with your key" : ""}`}
                </span>
              </span>
            )}
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              aria-label="Cloud API keys"
              className="relative inline-flex h-9 items-center gap-1.5 rounded-lg px-2 text-sm font-medium text-slate-600 transition hover:bg-slate-900/[0.05] hover:text-slate-900 active:scale-[0.97] sm:px-2.5 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-slate-100"
            >
              <svg className="h-[18px] w-[18px]" {...iconProps}>
                <path d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" />
              </svg>
              <span className="hidden sm:inline">API keys</span>
              {hasKeys && (
                <span className="absolute right-1 top-1.5 h-1.5 w-1.5 rounded-full bg-accent-500 sm:right-1.5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Language bar — each picker sits over its own pane */}
        <div className="relative grid grid-cols-[1fr_auto_1fr] items-center border-b border-slate-900/[0.06] md:grid-cols-2 dark:border-white/[0.06]">
          <div className="px-1.5 py-1.5 md:px-3">
            <LanguageSelect languages={languages} value={source} onChange={setSource} label="Translate from" />
          </div>
          <button
            type="button"
            onClick={swap}
            aria-label="Swap languages"
            className="z-10 mx-auto inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-900/[0.08] bg-white text-slate-500 shadow-[0_1px_2px_rgb(15_23_42/0.06)] transition hover:border-accent-300 hover:text-accent-600 active:scale-90 md:absolute md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2 dark:border-white/10 dark:bg-surface-dark dark:text-slate-400 dark:hover:border-accent-700 dark:hover:text-accent-300"
          >
            <svg className={`h-4 w-4 transition-transform duration-300 ${flip ? "rotate-180" : ""}`} {...iconProps}>
              <path d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
            </svg>
          </button>
          <div className="justify-self-end px-1.5 py-1.5 md:justify-self-stretch md:border-l md:border-slate-900/[0.06] md:px-3 dark:md:border-white/[0.06]">
            <LanguageSelect languages={languages} value={target} onChange={setTarget} label="Translate to" align="end" />
          </div>
        </div>

        {/* Panes */}
        <div className="grid overflow-hidden rounded-b-2xl md:grid-cols-2">
          {/* Input */}
          <div
            className="flex min-h-[9.5rem] cursor-text flex-col md:min-h-[16rem]"
            onClick={(e) => {
              if (e.target === e.currentTarget) taRef.current?.focus();
            }}
          >
            <label htmlFor="source-text" className="sr-only">
              Text to translate
            </label>
            <textarea
              id="source-text"
              ref={taRef}
              rows={3}
              value={input}
              lang={toBcp47(source)}
              dir="auto"
              onChange={(e) => setInput(e.target.value.slice(0, MAX_CHARS))}
              placeholder="Type or paste text to translate"
              className="scroll-thin block max-h-[55vh] w-full resize-none overflow-y-auto bg-transparent px-4 pt-4 text-[17px] leading-relaxed outline-none placeholder:text-slate-400 sm:px-5 md:text-lg dark:placeholder:text-slate-500"
            />
            {!input && (
              <div className="flex flex-wrap items-center gap-1.5 px-4 pb-1 pt-3 sm:px-5">
                <span className="mr-0.5 text-xs text-slate-500 dark:text-slate-400">Try</span>
                {SAMPLES.map((s) => (
                  <button
                    key={s.lang}
                    type="button"
                    onClick={() => applySample(s)}
                    className="group inline-flex max-w-full items-center gap-1.5 rounded-lg border border-slate-900/[0.08] px-2 py-1 text-[13px] text-slate-700 transition hover:border-accent-300 hover:bg-accent-50 hover:text-accent-800 active:scale-[0.97] dark:border-white/10 dark:text-slate-300 dark:hover:border-accent-800 dark:hover:bg-accent-950/50 dark:hover:text-accent-100"
                  >
                    <span className="font-mono text-[10px] font-medium text-slate-400 group-hover:text-accent-500">{s.tag}</span>
                    <span className="truncate" lang={toBcp47(s.lang)}>
                      {s.text}
                    </span>
                  </button>
                ))}
              </div>
            )}
            <div className="mt-auto flex h-12 items-center justify-between px-2 sm:px-3">
              {input ? (
                <button type="button" onClick={() => { setInput(""); taRef.current?.focus(); }} className={ghostBtn}>
                  <svg className="h-3.5 w-3.5" {...iconProps}>
                    <path d="M6 18 18 6M6 6l12 12" />
                  </svg>
                  Clear
                </button>
              ) : (
                <span />
              )}
              <span
                className={`px-2 text-xs tabular-nums ${input.length >= MAX_CHARS ? "text-red-500" : "text-slate-400 dark:text-slate-500"}`}
              >
                {input.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Output */}
          <div className="flex min-h-[9.5rem] flex-col border-t border-slate-900/[0.06] bg-slate-900/[0.02] md:min-h-[16rem] md:border-l md:border-t-0 dark:border-white/[0.06] dark:bg-white/[0.02]">
            <div aria-live="polite" className="flex-1 px-4 pt-4 text-[17px] leading-relaxed sm:px-5 md:text-lg">
              {result}
            </div>
            <div className="flex h-12 items-center justify-between px-2 sm:px-3">
              <span className="flex min-w-0 items-center gap-1.5 px-2 text-xs text-slate-500 dark:text-slate-400">
                {activeEngine && hasInput && output && !error && !stale && (
                  <>
                    <EngineIcon id={activeEngine.id} size={12} />
                    <span className="truncate">{activeEngine.name}</span>
                  </>
                )}
              </span>
              <button
                type="button"
                onClick={copyOutput}
                disabled={!hasInput || !output || !!error || stale}
                className={`${ghostBtn} disabled:pointer-events-none disabled:opacity-0`}
              >
                {copied ? (
                  <svg className="h-3.5 w-3.5 text-accent-600 dark:text-accent-400" {...iconProps}>
                    <path d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                ) : (
                  <svg className="h-3.5 w-3.5" {...iconProps}>
                    <rect x="8" y="8" width="12" height="12" rx="2" />
                    <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
                  </svg>
                )}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
          </div>
        </div>
      </section>

      {offline && (
        <div className="mt-3 flex items-start gap-2.5 rounded-xl border border-slate-900/[0.08] bg-white px-4 py-3 text-sm text-slate-600 dark:border-white/10 dark:bg-surface-dark dark:text-slate-400">
          <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-500" aria-hidden="true" />
          <span>
            Can’t reach the translation server. If you run it yourself, start the backend
            (<code className="font-mono text-[13px]">uvicorn main:app</code>) and reload.
          </span>
        </div>
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
