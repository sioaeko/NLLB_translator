import Translator from "@/components/Translator";
import ThemeToggle from "@/components/ThemeToggle";
import Logo from "@/components/Logo";

export default function Home() {
  return (
    <main className="min-h-screen">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
        <div className="flex items-center gap-2.5">
          <Logo size={36} />
          <div>
            <h1 className="text-[15px] font-bold leading-tight">NLLB Translator</h1>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              multi-engine · 200 languages
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <a
            href="https://github.com/sioaeko/NLLB_translator"
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-200 bg-white/70 p-2 text-slate-600 shadow-sm backdrop-blur transition hover:bg-white dark:border-slate-700 dark:bg-slate-900/70 dark:text-slate-300 dark:hover:bg-slate-800"
            aria-label="GitHub repository"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.5.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.5 9.5 0 015 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0022 12c0-5.52-4.48-10-10-10z" />
            </svg>
          </a>
          <ThemeToggle />
        </div>
      </header>

      <section className="mx-auto max-w-3xl px-5 pb-7 pt-6 text-center">
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/60 px-3 py-1 text-xs font-medium text-slate-600 backdrop-blur dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Local models + free cloud APIs
        </div>
        <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">
          One translator,{" "}
          <span className="bg-gradient-to-r from-indigo-500 to-violet-600 bg-clip-text text-transparent">
            every engine
          </span>
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-balance text-sm text-slate-500 dark:text-slate-400">
          Translate across 200 languages with open models that run on your machine
          (NLLB-200, MADLAD-400, Qwen via Ollama), or a free frontier API (Gemini,
          Groq) — pick your engine per translation.
        </p>
      </section>

      <section className="px-5 pb-16">
        <Translator />
      </section>

      <footer className="border-t border-slate-200/70 py-6 text-center text-xs text-slate-400 dark:border-slate-800">
        Engines: NLLB-200 · MADLAD-400 · Ollama · Gemini · Groq · Free &amp; open source (MIT)
      </footer>
    </main>
  );
}
