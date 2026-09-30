import Translator from "@/components/Translator";
import ThemeToggle from "@/components/ThemeToggle";
import Logo from "@/components/Logo";

const GITHUB = "https://github.com/sioaeko/NLLB_translator";

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex w-full max-w-4xl items-center justify-between px-4 pt-4 sm:px-6 sm:pt-6">
        <a href="/" className="-m-1 flex items-center gap-2.5 rounded-lg p-1">
          <Logo size={30} />
          <span className="text-[15px] font-semibold tracking-tight">NLLB Translator</span>
        </a>
        <div className="flex items-center gap-0.5">
          <a
            href={GITHUB}
            target="_blank"
            rel="noreferrer"
            aria-label="Source code on GitHub"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-900/[0.05] hover:text-slate-900 active:scale-95 dark:text-slate-400 dark:hover:bg-white/[0.06] dark:hover:text-slate-100"
          >
            <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.5.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02a9.5 9.5 0 015 0c1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0022 12c0-5.52-4.48-10-10-10z" />
            </svg>
          </a>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl flex-1 px-4 pb-16 sm:px-6">
        <div className="pb-5 pt-7 sm:pb-7 sm:pt-12">
          <h1 className="text-[1.75rem] font-semibold leading-[1.1] tracking-[-0.025em] sm:text-[2.5rem]">
            One translator,{" "}
            <span className="text-accent-600 dark:text-accent-400">every engine.</span>
          </h1>
          <p className="mt-2.5 max-w-[56ch] text-[15px] leading-relaxed text-slate-600 dark:text-slate-400">
            200 languages. Open models that run on this server, or cloud models
            with your own key — switch engine per translation.
          </p>
        </div>

        <Translator />
      </main>

      <footer className="mx-auto flex w-full max-w-4xl flex-col gap-1 px-4 pb-8 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <span>NLLB-200 · Hy-MT2 · Gemini · Qwen · GPT-OSS · GPT-6 Luna. MIT licensed.</span>
        <a
          href={GITHUB}
          target="_blank"
          rel="noreferrer"
          className="w-fit underline-offset-4 transition hover:text-slate-900 hover:underline dark:hover:text-slate-200"
        >
          Source on GitHub
        </a>
      </footer>
    </div>
  );
}
