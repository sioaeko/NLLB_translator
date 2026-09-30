import type { Config } from "tailwindcss";
import defaultTheme from "tailwindcss/defaultTheme";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // The one accent, derived from the logo blue (#2F80ED).
        accent: {
          50: "#EFF5FE",
          100: "#DCE9FC",
          200: "#BCD5F9",
          300: "#8EB9F4",
          400: "#5B99EE",
          500: "#2F80ED",
          600: "#1F6AD4",
          700: "#1B55A8",
          800: "#1B4785",
          900: "#1B3B6B",
          950: "#122544",
        },
        canvas: { DEFAULT: "#F6F7F9", dark: "#0A0E14" },
        surface: { dark: "#10151D", raised: "#141A23" },
      },
      fontFamily: {
        // Geist for Latin UI text; Pretendard picks up Hangul; system fonts cover
        // every other script the translator can output.
        sans: [
          "var(--font-geist)",
          '"Pretendard Variable"',
          "Pretendard",
          ...defaultTheme.fontFamily.sans,
        ],
        mono: ["var(--font-geist-mono)", ...defaultTheme.fontFamily.mono],
      },
      keyframes: {
        loading: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(400%)" },
        },
        "pop-in": {
          "0%": { opacity: "0", transform: "translateY(-4px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
      },
      animation: {
        loading: "loading 1.1s ease-in-out infinite",
        "pop-in": "pop-in 140ms cubic-bezier(0.2, 0.8, 0.2, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
