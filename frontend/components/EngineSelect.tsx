"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { Engine } from "@/lib/types";
import { KEY_LABEL } from "@/lib/engines";
import EngineIcon from "./EngineIcon";

// Short, scannable blurbs for the picker; falls back to the server description
// (OpenRouter's shows the chosen model).
const BLURB: Record<string, string> = {
  nllb: "Meta · 200 languages · fastest",
  hymt: "Tencent · 38 languages · most natural",
  ollama: "Google · 55 languages · runs on this server",
  gemini: "Google · free tier · strong on Korean & CJK",
  groq_qwen: "Alibaba · free on Groq · strong on CJK",
  groq_gptoss: "OpenAI open-weight · free on Groq",
  openai: "OpenAI · $0.10 / $0.50 per 1M tokens",
};

interface Props {
  engines: Engine[];
  value: string;
  onChange: (id: string) => void;
  onRequestKey: () => void;
  loading?: boolean;
}

function IconChip({ id }: { id: string }) {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[9px] bg-slate-900/[0.04] text-slate-700 ring-1 ring-inset ring-slate-900/[0.06] dark:bg-white/[0.06] dark:text-slate-200 dark:ring-white/[0.08]">
      <EngineIcon id={id} size={16} />
    </span>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export default function EngineSelect({ engines, value, onChange, onRequestKey, loading }: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const uid = useId();
  const listId = `${uid}-list`;
  const optId = (i: number) => `${uid}-opt-${i}`;

  const selected = engines.find((e) => e.id === value);

  const groups = useMemo(
    () =>
      [
        { key: "local", label: "Open models", note: "run on this server", items: engines.filter((e) => e.kind === "local") },
        { key: "api", label: "Cloud APIs", note: "use your own key", items: engines.filter((e) => e.kind === "api") },
      ].filter((g) => g.items.length > 0),
    [engines]
  );
  const flat = useMemo(() => groups.flatMap((g) => g.items), [groups]);

  function close(returnFocus: boolean) {
    setOpen(false);
    if (returnFocus) triggerRef.current?.focus();
  }

  function openList() {
    if (!flat.length) return;
    const current = flat.findIndex((e) => e.id === value);
    setActive(current >= 0 ? current : Math.max(0, flat.findIndex((e) => e.available)));
    setOpen(true);
  }

  function activate(e: Engine) {
    if (e.available) {
      onChange(e.id);
      close(true);
    } else if (e.kind === "api") {
      close(false);
      onRequestKey();
    }
  }

  // Close on outside click.
  useEffect(() => {
    function onDown(ev: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(ev.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  // Move focus into the list when it opens; keep the active option in view.
  useEffect(() => {
    if (open) listRef.current?.focus();
  }, [open]);
  useEffect(() => {
    if (open) document.getElementById(optId(active))?.scrollIntoView({ block: "nearest" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, open]);

  function onListKey(ev: React.KeyboardEvent) {
    const n = flat.length;
    if (!n) return;
    switch (ev.key) {
      case "ArrowDown":
        ev.preventDefault();
        setActive((a) => (a + 1) % n);
        break;
      case "ArrowUp":
        ev.preventDefault();
        setActive((a) => (a - 1 + n) % n);
        break;
      case "Home":
        ev.preventDefault();
        setActive(0);
        break;
      case "End":
        ev.preventDefault();
        setActive(n - 1);
        break;
      case "Enter":
      case " ":
        ev.preventDefault();
        activate(flat[active]);
        break;
      case "Escape":
        ev.preventDefault();
        close(true);
        break;
      case "Tab":
        setOpen(false);
        break;
    }
  }

  if (loading) {
    return (
      <div className="flex h-11 items-center gap-2.5 pl-1.5 pr-3" aria-hidden="true">
        <span className="skeleton h-8 w-8 rounded-[9px]" />
        <span className="flex flex-col gap-1.5">
          <span className="skeleton h-2 w-10 rounded-full" />
          <span className="skeleton h-3 w-28 rounded-full" />
        </span>
      </div>
    );
  }

  let index = -1;

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        id="engine-trigger"
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        onClick={() => (open ? close(false) : openList())}
        onKeyDown={(ev) => {
          if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
            ev.preventDefault();
            openList();
          }
        }}
        className="group flex h-11 items-center gap-2.5 rounded-xl pl-1.5 pr-2.5 text-left transition hover:bg-slate-900/[0.04] active:scale-[0.98] dark:hover:bg-white/[0.05]"
      >
        {selected ? (
          <IconChip id={selected.id} />
        ) : (
          <span className="h-8 w-8 rounded-[9px] bg-slate-900/[0.04] dark:bg-white/[0.06]" />
        )}
        <span className="flex min-w-0 flex-col leading-tight">
          <span className="text-[11px] text-slate-500 dark:text-slate-400">Engine</span>
          <span className="max-w-[11rem] truncate text-sm font-medium text-slate-900 dark:text-slate-100">
            {selected ? selected.name : "Choose an engine"}
          </span>
        </span>
        <Chevron open={open} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-30 mt-1.5 w-[min(22rem,calc(100vw-2rem))] origin-top-left animate-pop-in rounded-xl border border-slate-900/[0.08] bg-white p-1.5 shadow-[0_18px_44px_-14px_rgb(15_23_42/0.28)] dark:border-white/10 dark:bg-surface-raised dark:shadow-[0_18px_44px_-14px_rgb(0_0_0/0.75)]">
          <div
            ref={listRef}
            id={listId}
            role="listbox"
            tabIndex={-1}
            aria-label="Translation engine"
            aria-activedescendant={optId(active)}
            onKeyDown={onListKey}
            className="scroll-thin max-h-[min(60vh,28rem)] overflow-y-auto outline-none"
          >
            {groups.map((g) => (
              <div key={g.key} role="group" aria-labelledby={`${uid}-${g.key}`} className="pb-1 last:pb-0">
                <div id={`${uid}-${g.key}`} className="flex items-baseline gap-1.5 px-2.5 pb-1 pt-2 text-xs">
                  <span className="font-medium text-slate-700 dark:text-slate-300">{g.label}</span>
                  <span className="text-slate-400 dark:text-slate-500">· {g.note}</span>
                </div>
                {g.items.map((e) => {
                  index += 1;
                  const i = index;
                  const isActive = i === active;
                  const isSelected = e.id === value;
                  const needsKey = !e.available && e.kind === "api";
                  const notInstalled = !e.available && e.kind === "local";
                  const blurb = needsKey
                    ? `Add your ${KEY_LABEL[e.key_field] ?? "API"} key to use it`
                    : notInstalled
                      ? "Not installed on this server"
                      : BLURB[e.id] ?? e.description;
                  return (
                    <div
                      key={e.id}
                      id={optId(i)}
                      role="option"
                      aria-selected={isSelected}
                      aria-disabled={notInstalled || undefined}
                      title={notInstalled ? e.setup_hint : undefined}
                      onMouseEnter={() => setActive(i)}
                      onClick={() => activate(e)}
                      className={`flex items-center gap-3 rounded-md px-2 py-1.5 ${
                        notInstalled ? "cursor-not-allowed" : "cursor-pointer"
                      } ${isActive ? "bg-slate-900/[0.045] dark:bg-white/[0.06]" : ""}`}
                    >
                      <span className={notInstalled || needsKey ? "opacity-45 grayscale" : ""}>
                        <IconChip id={e.id} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span
                          className={`block truncate text-sm font-medium ${
                            notInstalled || needsKey
                              ? "text-slate-500 dark:text-slate-400"
                              : "text-slate-900 dark:text-slate-100"
                          }`}
                        >
                          {e.name}
                        </span>
                        <span className="block truncate text-xs text-slate-500 dark:text-slate-400">{blurb}</span>
                      </span>
                      {isSelected && (
                        <svg className="h-4 w-4 shrink-0 text-accent-600 dark:text-accent-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                          <path
                            fillRule="evenodd"
                            d="M16.7 5.3a1 1 0 010 1.4l-8 8a1 1 0 01-1.4 0l-4-4a1 1 0 011.4-1.4L8 12.6l7.3-7.3a1 1 0 011.4 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                      {needsKey && (
                        <span className="shrink-0 rounded-md px-1.5 py-0.5 text-xs font-medium text-accent-600 dark:text-accent-400">
                          Add key
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
