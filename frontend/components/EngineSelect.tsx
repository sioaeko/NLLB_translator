"use client";

import { useEffect, useRef, useState } from "react";
import type { Engine } from "@/lib/types";
import EngineIcon from "./EngineIcon";

function IconChip({ id }: { id: string }) {
  return (
    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
      <EngineIcon id={id} />
    </span>
  );
}

interface Props {
  engines: Engine[];
  value: string;
  onChange: (id: string) => void;
}

function KindBadge({ engine }: { engine: Engine }) {
  const isLocal = engine.kind === "local";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        isLocal
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400"
          : "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-400"
      }`}
    >
      {engine.private && (
        <svg className="h-2.5 w-2.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 1a5 5 0 00-5 5v3H6a2 2 0 00-2 2v9a2 2 0 002 2h12a2 2 0 002-2v-9a2 2 0 00-2-2h-1V6a5 5 0 00-5-5zm3 8H9V6a3 3 0 016 0v3z" />
        </svg>
      )}
      {isLocal ? "Local" : "Free API"}
    </span>
  );
}

export default function EngineSelect({ engines, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = engines.find((e) => e.id === value);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium shadow-sm transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800/70 dark:hover:border-slate-600"
      >
        {selected ? (
          <IconChip id={selected.id} />
        ) : (
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-400 dark:bg-slate-800">?</span>
        )}
        <span className="max-w-[9rem] truncate">
          {selected ? selected.name : "No engine"}
        </span>
        {selected && <KindBadge engine={selected} />}
        <svg
          className={`h-4 w-4 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div className="absolute left-0 z-30 mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
          <div className="border-b border-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:border-slate-800">
            Translation engine
          </div>
          <ul className="scroll-thin max-h-[60vh] overflow-y-auto py-1">
            {engines.map((e) => {
              const disabled = !e.available;
              return (
                <li key={e.id}>
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => {
                      onChange(e.id);
                      setOpen(false);
                    }}
                    className={`flex w-full gap-2.5 px-3 py-2.5 text-left transition ${
                      disabled
                        ? "cursor-not-allowed opacity-45"
                        : "hover:bg-slate-50 dark:hover:bg-slate-800"
                    } ${e.id === value ? "bg-indigo-50/60 dark:bg-indigo-500/10" : ""}`}
                  >
                    <div className="mt-0.5">
                      <IconChip id={e.id} />
                    </div>
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold">{e.name}</span>
                        <KindBadge engine={e} />
                      </div>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {e.description}
                      </span>
                      {disabled && (
                        <span className="text-[11px] font-medium text-amber-600 dark:text-amber-500">
                          {e.setup_hint || "Not configured"}
                        </span>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
