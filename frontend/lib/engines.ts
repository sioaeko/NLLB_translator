// Client-side knowledge about the cloud engines' keys and providers.

/** Stored key names that unlock cloud engines (matches the backend's key_field). */
export const KEY_FIELDS = ["gemini", "groq", "openrouter", "openai"] as const;

/** How the key is referred to in the UI ("Add your Groq key"). */
export const KEY_LABEL: Record<string, string> = {
  gemini: "Gemini",
  groq: "Groq",
  openrouter: "OpenRouter",
  openai: "OpenAI",
};

/** Who receives the text when that engine is used ("Sent to Google"). */
export const SENT_TO: Record<string, string> = {
  gemini: "Google",
  groq: "Groq",
  openrouter: "OpenRouter",
  openai: "OpenAI",
};

export const OPENROUTER_MODEL_KEY = "openrouter_model";
export const DEFAULT_OPENROUTER_MODEL = "google/gemma-4-31b-it:free";

/** USD per 1M input / output tokens; checked October 2, 2026. Rates can change. */
export const OPENROUTER_PRESETS = [
  { id: "google/gemma-4-31b-it:free", label: "Gemma 4 31B", price: "free" },
  { id: "google/gemma-4-26b-a4b-it:free", label: "Gemma 4 26B A4B", price: "free" },
  { id: "qwen/qwen3.8-27b:free", label: "Qwen 3.8 27B", price: "free" },
  { id: "nvidia/nemotron-3.5-lightning:free", label: "Nemotron 3.5 Lightning", price: "free" },
  { id: "deepseek/deepseek-v4-flash", label: "DeepSeek V4 Flash", price: "$0.042 / $0.084" },
  { id: "deepseek/deepseek-v4.1-flash", label: "DeepSeek V4.1 Flash", price: "$0.01725 / $0.75" },
  { id: "qwen/qwen3.8-flash", label: "Qwen 3.8 Flash", price: "$0.15 / $0.47" },
  { id: "z-ai/glm-5.3-flash", label: "GLM 5.3 Flash", price: "$0.15 / $0.50" },
  { id: "openai/gpt-6-luna", label: "GPT-6 Luna", price: "$0.10 / $0.50" },
];

export function openRouterLabel(id: string): string {
  const preset = OPENROUTER_PRESETS.find((p) => p.id === id);
  return preset ? `${preset.label} (${preset.price})` : id;
}
