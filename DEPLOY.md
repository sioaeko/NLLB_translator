# Deployment

Two supported shapes. **HuggingFace Spaces** (single free container) is the
recommended one for a live demo.

---

## Option A — HuggingFace Spaces (free, single container)

The root [`Dockerfile`](Dockerfile) builds everything into one image: the static
Next.js frontend, the FastAPI backend, and a pre-converted NLLB model. FastAPI
serves the UI and the API from the same origin, so no CORS or separate frontend
host is needed.

1. Create a new Space → **SDK: Docker** → **Blank**.
2. Push this repo to the Space (or connect the GitHub repo).
3. Add the Space metadata to the **top of the Space's `README.md`**:

   ```yaml
   ---
   title: NLLB Translator
   emoji: 🌐
   colorFrom: indigo
   colorTo: purple
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```

4. **(Optional) Enable the free API engines** — add repo *Secrets* in Space settings:
   - `GEMINI_API_KEY` — from <https://aistudio.google.com/apikey> (free, no card)
   - `GROQ_API_KEY` — from <https://console.groq.com/keys> (free, no card)

   Without these, only the local **NLLB** engine shows up — which is enough for a
   working demo. Add the keys to unlock the Gemini / Groq engines in the dropdown.

**Notes**
- First build downloads + converts the model (~2.4 GB) — a one-time slow build.
- Free CPU Spaces sleep after ~2 days idle; they wake on the next visit.
- The NLLB engine is light enough for the free CPU tier. Heavier local engines
  (e.g. MADLAD-400) should be run on your own machine / a GPU host instead.

---

## Option B — Split: Vercel (frontend) + Space/host (backend)

1. **Backend** anywhere that runs the [`backend/Dockerfile`](backend/Dockerfile)
   (a Docker Space, Render, Fly.io…). Set API-key secrets as needed.
2. **Frontend** on Vercel: set `NEXT_PUBLIC_API_BASE` to the backend URL, deploy
   the `frontend/` directory. (Leave `NEXT_OUTPUT_EXPORT` unset so Vercel builds
   a normal Next app.)
3. Set `CORS_ORIGINS` on the backend to your Vercel URL.

---

## Local (Docker Compose)

```bash
cp backend/.env.example backend/.env   # optional: add API keys
docker compose up --build
```

Frontend on <http://localhost:3000>, backend on <http://localhost:8000>.
