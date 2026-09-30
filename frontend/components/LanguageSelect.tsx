"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { Language } from "@/lib/types";

// Pinned at the top when the search box is empty.
const COMMON = ["eng_Latn", "kor_Hang", "jpn_Jpan", "zho_Hans", "spa_Latn", "fra_Latn", "deu_Latn"];

interface Props {
  languages: Language[];
  value: string;
  onChange: (code: string) => void;
  label: string;
  /** "end" anchors the panel right on mobile and left from md up (target side). */
  align?: "start" | "end";
}

export default function LanguageSelect({ languages, value, onChange, label, align = "start" }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const uid = useId();
  const listId = `${uid}-list`;
  const optId = (i: number) => `${uid}-opt-${i}`;

  const selected = languages.find((l) => l.code === value);

  const sections = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q) {
      const hits = languages.filter(
        (l) => l.name.toLowerCase().includes(q) || l.code.toLowerCase().includes(q)
      );
      return hits.length ? [{ label: "", items: hits }] : [];
    }
    const common = COMMON.map((c) => languages.find((l) => l.code === c)).filter(Boolean) as Language[];
    const rest = languages.filter((l) => !COMMON.includes(l.code));
    return [
      { label: "Common", items: common },
      { label: "All languages", items: rest },
    ].filter((s) => s.items.length);
  }, [languages, query]);
  const flat = useMemo(() => sections.flatMap((s) => s.items), [sections]);

  function close(returnFocus: boolean) {
    setOpen(false);
    setQuery("");
    if (returnFocus) triggerRef.current?.focus();
  }

  function choose(code: string) {
    onChange(code);
    close(true);
  }

  useEffect(() => {
    function onDown(ev: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(ev.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  // Start on the current language; reset to the top whenever the query changes.
  useEffect(() => {
    if (!open) return;
    if (query) setActive(0);
    else setActive(Math.max(0, flat.findIndex((l) => l.code === value)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, query]);
  useEffect(() => {
    if (open) document.getElementById(optId(active))?.scrollIntoView({ block: "nearest" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, open]);

  function onKey(ev: React.KeyboardEvent) {
    const n = flat.length;
    switch (ev.key) {
      case "ArrowDown":
        ev.preventDefault();
        if (n) setActive((a) => (a + 1) % n);
        break;
      case "ArrowUp":
        ev.preventDefault();
        if (n) setActive((a) => (a - 1 + n) % n);
        break;
      case "Enter":
        ev.preventDefault();
        if (flat[active]) choose(flat[active].code);
        break;
      case "Escape":
        ev.preventDefault();
        close(true);
        break;
      case "Tab":
        close(false);
        break;
    }
  }

  const panelPos = align === "end" ? "right-0 md:left-0 md:right-auto" : "left-0";
  let index = -1;

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`${label}: ${selected?.name ?? "not selected"}`}
        onClick={() => (open ? close(false) : setOpen(true))}
        onKeyDown={(ev) => {
          if (ev.key === "ArrowDown") {
            ev.preventDefault();
            setOpen(true);
          }
        }}
        className="flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-[15px] font-medium text-slate-800 transition hover:bg-slate-900/[0.04] active:scale-[0.98] dark:text-slate-100 dark:hover:bg-white/[0.05]"
      >
        {selected ? (
          selected.name
        ) : (
          <span className="skeleton inline-block h-3 w-16 rounded-full" aria-hidden="true" />
        )}
        <svg
          className={`h-4 w-4 text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
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
      </button>

      {open && (
        <div
          className={`absolute top-full z-30 mt-1.5 w-[min(18rem,calc(100vw-2rem))] animate-pop-in overflow-hidden rounded-xl border border-slate-900/[0.08] bg-white shadow-[0_18px_44px_-14px_rgb(15_23_42/0.28)] dark:border-white/10 dark:bg-surface-raised dark:shadow-[0_18px_44px_-14px_rgb(0_0_0/0.75)] ${panelPos}`}
        >
          <div className="flex items-center gap-2 border-b border-slate-900/[0.06] px-3 dark:border-white/[0.07]">
            <svg className="h-4 w-4 shrink-0 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l3.08 3.08a.75.75 0 11-1.06 1.06l-3.08-3.08A7 7 0 012 9z"
                clipRule="evenodd"
              />
            </svg>
            <input
              autoFocus
              role="combobox"
              aria-expanded="true"
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={flat.length ? optId(active) : undefined}
              aria-label={`Search ${label.toLowerCase()}`}
              value={query}
              onChange={(ev) => setQuery(ev.target.value)}
              onKeyDown={onKey}
              placeholder="Search 200 languages"
              className="h-10 w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
            />
          </div>
          {flat.length === 0 && (
            <p className="px-4 py-3 text-sm text-slate-500">No language matches “{query}”.</p>
          )}
          <ul id={listId} role="listbox" aria-label={label} className="scroll-thin max-h-72 overflow-y-auto p-1.5 empty:hidden">
            {sections.map((s) => (
              <li key={s.label || "results"} role={s.label ? "group" : "presentation"} aria-label={s.label || undefined}>
                {s.label && (
                  <div aria-hidden="true" className="px-2.5 pb-1 pt-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                    {s.label}
                  </div>
                )}
                <ul role="presentation">
                  {s.items.map((l) => {
                    index += 1;
                    const i = index;
                    const isSel = l.code === value;
                    return (
                      <li
                        key={l.code}
                        id={optId(i)}
                        role="option"
                        aria-selected={isSel}
                        onMouseEnter={() => setActive(i)}
                        onMouseDown={(ev) => ev.preventDefault()}
                        onClick={() => choose(l.code)}
                        className={`flex cursor-pointer items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-sm ${
                          i === active ? "bg-slate-900/[0.045] dark:bg-white/[0.06]" : ""
                        } ${isSel ? "font-medium text-accent-700 dark:text-accent-300" : "text-slate-700 dark:text-slate-200"}`}
                      >
                        <span className="truncate">{l.name}</span>
                        <span className="shrink-0 font-mono text-[11px] text-slate-400">{l.code}</span>
                      </li>
                    );
                  })}
                </ul>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
