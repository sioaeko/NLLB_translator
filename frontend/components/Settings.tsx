"use client";

import { useEffect, useState } from "react";
import type { ApiKeys } from "@/lib/types";

interface Props {
  open: boolean;
  keys: ApiKeys;
  onClose: () => void;
  onSave: (keys: ApiKeys) => void;
}

const FIELDS = [
  {
    field: "gemini",
    label: "Google Gemini API key",
    unlocks: "Gemini 2.5",
    href: "https://aistudio.google.com/apikey",
    placeholder: "AIza…",
  },
  {
    field: "groq",
    label: "Groq API key",
    unlocks: "Qwen 2.5 · Llama 3.3",
    href: "https://console.groq.com/keys",
    placeholder: "gsk_…",
  },
];

export default function Settings({ open, keys, onClose, onSave }: Props) {
  const [draft, setDraft] = useState<ApiKeys>(keys);

  useEffect(() => {
    if (open) setDraft(keys);
  }, [open, keys]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-base font-bold">API keys</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
          Paste your own free-tier keys to unlock the cloud engines. Keys are stored
          only in this browser and sent directly with each request — never saved on
          the server.
        </p>

        <div className="space-y-4">
          {FIELDS.map((f) => (
            <div key={f.field}>
              <div className="mb-1 flex items-center justify-between">
                <label className="text-sm font-medium">{f.label}</label>
                <a
                  href={f.href}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  get a free key ↗
                </a>
              </div>
              <input
                type="password"
                value={draft[f.field] || ""}
                onChange={(e) => setDraft({ ...draft, [f.field]: e.target.value })}
                placeholder={f.placeholder}
                autoComplete="off"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700 dark:bg-slate-800"
              />
              <p className="mt-1 text-[11px] text-slate-400">Unlocks: {f.unlocks}</p>
            </div>
          ))}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(draft)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
