# Single-container build: Next.js static frontend + FastAPI backend + NLLB model,
# suitable for a HuggingFace Space (Docker SDK) or any single-host deploy.

# ---- Stage 1: build the static frontend ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
# Same-origin API calls; export a static site.
ENV NEXT_OUTPUT_EXPORT=1
ENV NEXT_PUBLIC_API_BASE=
RUN npm run build   # produces /fe/out

# ---- Stage 2: convert NLLB to CTranslate2 int8 (needs torch, build-only) ----
FROM python:3.11-slim AS model
WORKDIR /m
COPY backend/requirements.txt backend/requirements-convert.txt backend/convert_model.py ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r requirements-convert.txt --extra-index-url https://download.pytorch.org/whl/cpu
# CTranslate2 wheels ship a .so that requests an executable stack, which hardened
# container runtimes (incl. HuggingFace Spaces) refuse. Clear the flag.
RUN apt-get update && apt-get install -y --no-install-recommends patchelf \
 && find /usr/local/lib/python3.11/site-packages -name '*.so*' -path '*ctranslate2*' -exec patchelf --clear-execstack {} + \
 && apt-get purge -y patchelf && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
RUN python convert_model.py   # writes ./models/nllb-200-distilled-600M-int8

# ---- Stage 3: lean runtime (no torch) ----
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV STATIC_DIR=/app/static \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Same execstack fix for the runtime inference library.
RUN apt-get update && apt-get install -y --no-install-recommends patchelf \
 && find /usr/local/lib/python3.11/site-packages -name '*.so*' -path '*ctranslate2*' -exec patchelf --clear-execstack {} + \
 && apt-get purge -y patchelf && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
COPY backend/ ./
COPY --from=model /m/models ./models
COPY --from=frontend /fe/out ./static
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
