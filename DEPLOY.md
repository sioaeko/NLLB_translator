# Deployment

Two supported shapes. **HuggingFace Spaces** (single container) is the
recommended one for a live demo.

---

## Option A — HuggingFace Spaces (single container)

The root [`Dockerfile`](Dockerfile) builds everything into one image: the static
Next.js frontend, the FastAPI backend, and five local models (NLLB-200 as
CTranslate2 int8, Hy-MT2 as a ~1.1 GB GGUF run by llama.cpp, plus TranslateGemma
4B ~3.3 GB, Qwen3.5 2B ~1.9 GB, and Qwen3 1.7B ~1.4 GB through Ollama). FastAPI serves the
UI and the API from the same origin, so there's no CORS setup or separate
frontend host.

1. Create a Space → **SDK: Docker** → **Blank**.
   > As of 2026, HuggingFace asks for a PRO subscription to *create* a new Docker
   > Space on free CPU hardware. An existing Docker Space keeps running and can
   > still be updated for free.
2. Upload the repo to the Space — `backend/deploy_hf.py` does this and adds the
   Space metadata below:

   ```bash
   cd backend
   HF_TOKEN=hf_… SPACE_ID=<user>/nllb-translator python deploy_hf.py
   ```

   Or add the metadata to the top of the Space's `README.md` yourself:

   ```yaml
   ---
   title: NLLB Translator
   emoji: 🌐
   colorFrom: blue
   colorTo: blue
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```

3. **(Optional) Server-side keys** — add Space *Secrets* to turn cloud engines on
   for every visitor:
   - `GEMINI_API_KEY` — <https://aistudio.google.com/apikey> (free tier)
   - `GROQ_API_KEY` — <https://console.groq.com/keys> (free tier)
   - `OPENROUTER_API_KEY` — <https://openrouter.ai/keys>
   - `OPENAI_API_KEY` — <https://platform.openai.com/api-keys> (paid)

   You don't need any of them: all five local engines work out of the box, and
   visitors can paste their own keys in the app's **API keys** panel. Be careful
   with server-side paid keys on a public Space — every visitor spends them.

**Notes**
- The first build downloads the models (NLLB ~2.4 GB to convert, Hy-MT2 ~1.1 GB,
  TranslateGemma ~3.3 GB, Qwen3.5 2B ~1.9 GB, Qwen3 1.7B ~1.4 GB) and the pinned
  Ollama runtime. The Qwen tags are `qwen3.5:2b-q4_K_M` and `qwen3:1.7b`.
- Docker also compiles a llama.cpp CPU wheel against Debian's libc and verifies
  that it loads before publishing the image; later builds can reuse this layer.
- Free CPU Spaces sleep after ~2 days idle and wake on the next visit; the first
  translation after a wake-up also includes model-loading time.
- Ollama binds only to `127.0.0.1:11434`; visitors use it through the translation
  API. Ollama cloud features are disabled. A supervisor starts both services and
  shuts down the container if either service exits.
- Ollama loads at most one model and runs one inference at a time. All three
  Ollama engines use a 4K context, 2 CPU threads, and unload after 10 idle minutes
  (`OLLAMA_KEEP_ALIVE=10m`) to reduce reloads when reusing the same model.
  Qwen thinking is disabled for translation. All model files are already in the
  image when a Space wakes up; switching models may add loading time.
- `HYMT_THREADS=2` and `CT2_THREADS=2` also limit Hy-MT2 and NLLB to the free
  Space's CPU allocation. Hy-MT2 uses that limit for both prompt processing and
  generation; NLLB uses one worker with beam size 4. Outside this image, leaving
  either variable at 0 detects CPU affinity and cgroup v1/v2 quotas.
- All local engines share one inference slot within the backend process.
  Concurrent translations wait instead of running competing CPU inference jobs;
  completed cache hits can return without waiting. Keep one backend worker on a
  free CPU Space so each worker does not load its own models and inference slot.
- `OLLAMA_MODEL`, `OLLAMA_QWEN35_MODEL`, and `OLLAMA_QWEN3_MODEL` override the
  TranslateGemma, Qwen3.5, and Qwen3 tags respectively. Each configured model must
  be installed before the UI enables its engine; changing a runtime variable
  alone does not download a different model.
- On free CPU hardware (2 vCPU / 16 GB), the Ollama engines are intended for short
  translations; response times grow with text length and concurrent visitors.

### Streaming, caching and cancellation

The frontend calls `POST /api/translate/stream`, which returns newline-delimited
JSON (`application/x-ndjson`). LLM engines stream generated text; NLLB emits each
completed line. Partial output can appear before the full request finishes, but
cold starts and prompt processing still take time. The original
`POST /api/translate` JSON endpoint remains supported.

Local result caches are bounded and live only in server memory: up to 2,048
completed lines each for NLLB and Hy-MT2, and 256 completed translations per Ollama
engine. Restarting the backend clears them. The browser also retains up to 32
successful results in the current tab's memory; reloads or key/model-setting
changes clear that cache. Incomplete, failed and canceled generation results are
not cached, while already completed lines from a longer request can be reused.

Changing input or settings aborts the old browser stream and prevents stale
responses from appearing. Server cancellation is checked while waiting for the
inference slot and between streamed chunks. Hy-MT2 may finish the current
decoding step and NLLB finishes its active line before stopping. An Ollama/cloud
HTTP read can remain blocked until its next event or read timeout (120 seconds
for Ollama, 60 seconds for cloud translation calls). Closing the browser stream
does not guarantee immediate upstream termination.

If deploying behind another reverse proxy, disable response buffering for
`/api/translate/stream` so chunks can reach the browser promptly. Treat only the
terminal `done` event as success; later failures are sent as `error` events in
the stream, and an early connection close is incomplete.

---

## Option B — Split: Vercel (frontend) + Docker host (backend)

1. **Backend** anywhere that runs [`backend/Dockerfile`](backend/Dockerfile)
   (Render, Fly.io, a VM…). Set API-key secrets as needed. This backend-only image
   bundles NLLB and Hy-MT2. To enable the three Ollama engines, run a separate
   Ollama service, set `OLLAMA_HOST` to its reachable URL, and pull
   `translategemma:4b`, `qwen3.5:2b-q4_K_M`, and `qwen3:1.7b` there.
2. **Frontend** on Vercel: set `NEXT_PUBLIC_API_BASE` to the backend URL and
   deploy the `frontend/` directory. (Leave `NEXT_OUTPUT_EXPORT` unset so Vercel
   builds a normal Next app.)
3. Set `CORS_ORIGINS` on the backend to your Vercel URL.

---

## Local (Docker Compose)

```bash
cp backend/.env.example backend/.env   # optional: add API keys
docker compose up --build
```

Frontend on <http://localhost:3000>, backend on <http://localhost:8000>.
Compose uses the backend-only image; Ollama needs the separate service described
above. `OLLAMA_HOST` must be reachable from the backend container, not just from
the host browser.
