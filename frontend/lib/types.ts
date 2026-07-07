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
}

export interface TranslateResponse {
  translation: string;
  source: string;
  target: string;
  engine: string;
}
