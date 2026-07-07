export interface Language {
  code: string;
  name: string;
}

export interface Engine {
  id: string;
  name: string;
  kind: "local" | "api";
  description: string;
  available: boolean;
  private: boolean;
  setup_hint: string;
  key_field: string; // which stored key unlocks it ("gemini"/"groq"); "" for local
}

export type ApiKeys = Record<string, string>; // { gemini?: string, groq?: string }

export interface TranslateResponse {
  translation: string;
  source: string;
  target: string;
  engine: string;
}
