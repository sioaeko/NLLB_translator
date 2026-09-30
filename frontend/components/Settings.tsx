"use client";

import { useEffect, useId, useState } from "react";
import type { ApiKeys } from "@/lib/types";
import {
  DEFAULT_OPENROUTER_MODEL,
  OPENROUTER_MODEL_KEY,
  OPENROUTER_PRESETS,
} from "@/lib/engines";

interface Props {
  open: boolean;
  keys: ApiKeys;
  onClose: () => void;
  onSave: (keys: ApiKeys) => void;
}

const FIELDS = [
  {
    field: "gemini",
    label: "Google Gemini",
    unlocks: "Gemini 3.5 Flash-Lite · free tier",
    href: "https://aistudio.google.com/apikey",
    placeholder: "AIza…",
  },
  {
    field: "groq",
    label: "Groq",
    unlocks: "Qwen 3.8 27B and GPT-OSS 120B · free tier",
    href: "https://console.groq.com/keys",
    placeholder: "gsk_…",
  },
  {
    field: "openrouter",
    label: "OpenRouter",
    unlocks: "One key for hundreds of models, several free",
    href: "https://openrouter.ai/keys",
    placeholder: "sk-or-…",
  },
  {
    field: "openai",
    label: "OpenAI",
    unlocks: "GPT-6 Luna · $0.10 / $0.50 per 1M tokens",
    href: "https://platform.openai.com/api-keys",
    placeholder: "sk-…",
  },
];

const inputClass =
  "h-10 w-full rounded-lg border border-slate-900/10 bg-slate-900/[0.02] px-3 text-sm outline-none transition placeholder:text-slate-400 focus:border-accent-400 focus:bg-white focus:ring-4 focus:ring-accent-500/15 dark:border-white/10 dark:bg-white/[0.03] dark:focus:border-accent-500 dark:focus:bg-transparent";

const CUSTOM = "__custom__";

export default function Settings({ open, keys, onClose, onSave }: Props) {
  const [draft, setDraft] = useState<ApiKeys>(keys);
  const [customModel, setCustomModel] = useState(false);
  const uid = useId();

  useEffect(() => {
    if (!open) return;
    setDraft(keys);
    const m = keys[OPENROUTER_MODEL_KEY];
    setCustomModel(!!m && !OPENROUTER_PRESETS.some((p) => p.id === m));
  }, [open, keys]);

  useEffect(() => {
    if (!open) return;
    function onKey(ev: KeyboardEvent) {
      if (ev.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const model = draft[OPENROUTER_MODEL_KEY] || DEFAULT_OPENROUTER_MODEL;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-3 backdrop-blur-[2px] sm:items-center sm:p-4"
      onMouseDown={onClose}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${uid}-title`}
        aria-describedby={`${uid}-desc`}
        onMouseDown={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          onSave(draft);
        }}
        className="scroll-thin max-h-[92dvh] w-full max-w-md animate-pop-in overflow-y-auto rounded-2xl border border-slate-900/[0.08] bg-white p-5 shadow-[0_24px_60px_-20px_rgb(15_23_42/0.4)] sm:p-6 dark:border-white/10 dark:bg-surface-raised"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id={`${uid}-title`} className="text-base font-semibold tracking-tight">
              Cloud API keys
            </h2>
            <p id={`${uid}-desc`} className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Add a key to unlock that provider’s engines. Free tiers first.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="-mr-1.5 -mt-1 inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-900/[0.05] hover:text-slate-700 dark:hover:bg-white/[0.06] dark:hover:text-slate-200"
          >
            <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="mt-5 space-y-4">
          {FIELDS.map((f, i) => {
            const id = `${uid}-${f.field}`;
            const saved = !!keys[f.field];
            return (
              <div key={f.field}>
                <div className="mb-1.5 flex items-baseline justify-between gap-2">
                  <label htmlFor={id} className="text-sm font-medium">
                    {f.label}
                    {saved && (
                      <span className="ml-2 text-xs font-normal text-accent-600 dark:text-accent-400">Saved</span>
                    )}
                  </label>
                  <a
                    href={f.href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-medium text-accent-600 underline-offset-4 hover:underline dark:text-accent-400"
                  >
                    Get a key
                  </a>
                </div>
                <input
                  id={id}
                  autoFocus={i === 0}
                  type="password"
                  value={draft[f.field] || ""}
                  onChange={(e) => setDraft({ ...draft, [f.field]: e.target.value })}
                  placeholder={f.placeholder}
                  autoComplete="off"
                  spellCheck={false}
                  className={`${inputClass} font-mono`}
                />
                <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">{f.unlocks}</p>

                {f.field === "openrouter" && (
                  <div className="mt-3">
                    <label htmlFor={`${uid}-or-model`} className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-300">
                      OpenRouter model
                    </label>
                    <select
                      id={`${uid}-or-model`}
                      value={customModel ? CUSTOM : model}
                      onChange={(e) => {
                        if (e.target.value === CUSTOM) {
                          setCustomModel(true);
                          setDraft({ ...draft, [OPENROUTER_MODEL_KEY]: "" });
                        } else {
                          setCustomModel(false);
                          setDraft({ ...draft, [OPENROUTER_MODEL_KEY]: e.target.value });
                        }
                      }}
                      className={`${inputClass} appearance-none bg-[length:16px] bg-[right_0.6rem_center] bg-no-repeat pr-9`}
                      style={{
                        backgroundImage:
                          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%2394a3b8'%3E%3Cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3E%3C/svg%3E\")",
                      }}
                    >
                      {OPENROUTER_PRESETS.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label} — {p.price === "free" ? "free" : `${p.price} per 1M tokens`}
                        </option>
                      ))}
                      <option value={CUSTOM}>Another model…</option>
                    </select>
                    {customModel && (
                      <input
                        aria-label="OpenRouter model id"
                        value={draft[OPENROUTER_MODEL_KEY] || ""}
                        onChange={(e) => setDraft({ ...draft, [OPENROUTER_MODEL_KEY]: e.target.value })}
                        placeholder="vendor/model-name"
                        autoComplete="off"
                        spellCheck={false}
                        className={`${inputClass} mt-2 font-mono`}
                      />
                    )}
                    <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                      Free models are rate-limited by OpenRouter.{" "}
                      <a
                        href="https://openrouter.ai/models"
                        target="_blank"
                        rel="noreferrer"
                        className="font-medium text-accent-600 underline-offset-4 hover:underline dark:text-accent-400"
                      >
                        Browse models
                      </a>
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <p className="mt-5 flex items-start gap-2 rounded-lg bg-slate-900/[0.03] px-3 py-2.5 text-xs leading-relaxed text-slate-600 dark:bg-white/[0.04] dark:text-slate-400">
          <svg className="mt-px h-3.5 w-3.5 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path
              fillRule="evenodd"
              d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
              clipRule="evenodd"
            />
          </svg>
          Keys stay in this browser. Each request passes yours through to the provider;
          the server never stores it. Paid models bill your own account.
        </p>

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="h-9 rounded-lg px-3.5 text-sm font-medium text-slate-600 transition hover:bg-slate-900/[0.05] dark:text-slate-300 dark:hover:bg-white/[0.06]"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="h-9 rounded-lg bg-accent-600 px-4 text-sm font-medium text-white shadow-[0_1px_2px_rgb(31_106_212/0.4)] transition hover:bg-accent-700 active:scale-[0.98]"
          >
            Save keys
          </button>
        </div>
      </form>
    </div>
  );
}
