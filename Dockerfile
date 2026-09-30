# Single-container build: Next.js static frontend + FastAPI backend + local
# models (NLLB-200 via CTranslate2, Hy-MT2 via llama.cpp, TranslateGemma via Ollama), suitable for a
# HuggingFace Space (Docker SDK) or any single-host deploy.

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

# ---- Stage 2: prepare model files (torch is needed here only) ----
FROM python:3.11-slim AS model
WORKDIR /m
COPY backend/requirements.txt backend/requirements-convert.txt backend/convert_model.py backend/fetch_hymt.py ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r requirements-convert.txt --extra-index-url https://download.pytorch.org/whl/cpu
# CTranslate2 wheels ship a .so that requests an executable stack, which hardened
# container runtimes (incl. HuggingFace Spaces) refuse. Clear the flag.
RUN apt-get update && apt-get install -y --no-install-recommends patchelf \
 && find /usr/local/lib/python3.11/site-packages -name '*.so*' -path '*ctranslate2*' -exec patchelf --clear-execstack {} + \
 && apt-get purge -y patchelf && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
RUN python convert_model.py   # ./models/nllb-200-distilled-600M-int8
RUN python fetch_hymt.py      # ./models/hy-mt2-1.8b/Hy-MT2-1.8B-Q4_K_M.gguf (~1.1 GB)

# ---- Build llama.cpp against the same libc as the runtime ----
# The third-party CPU wheel can depend on musl, which Debian does not provide.
FROM python:3.11-slim AS llama
WORKDIR /build
COPY backend/requirements-llm.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
 && rm -rf /var/lib/apt/lists/*
RUN CMAKE_ARGS="-DGGML_NATIVE=OFF" CMAKE_BUILD_PARALLEL_LEVEL=2 \
    pip wheel --no-cache-dir --no-deps --no-binary=llama-cpp-python \
      -r requirements-llm.txt --wheel-dir /wheels

# ---- Ollama + model, downloaded once during the image build ----
FROM ollama/ollama:0.35.0@sha256:2a6e883b917fc543389599dae79918f5cac9e1438890506982f44aa4f5625d01 AS ollama-dist
FROM python:3.11-slim AS ollama-model
WORKDIR /prepare
COPY --from=ollama-dist /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama-dist /usr/lib/ollama /usr/lib/ollama
ENV OLLAMA_HOST=http://127.0.0.1:11434 \
    OLLAMA_MODELS=/opt/ollama/models \
    OLLAMA_MODEL=translategemma:4b \
    OLLAMA_NO_CLOUD=1
COPY backend/ollama_service.py ./
RUN python ollama_service.py --pull

# ---- Runtime (no torch or compiler) ----
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV STATIC_DIR=/app/static \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    OLLAMA_HOST=http://127.0.0.1:11434 \
    OLLAMA_MODELS=/opt/ollama/models \
    OLLAMA_MODEL=translategemma:4b \
    OLLAMA_NO_CLOUD=1 \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_MAX_QUEUE=8 \
    OLLAMA_CONTEXT_LENGTH=4096 \
    OLLAMA_TRANSLATE_THREADS=2 \
    OLLAMA_KEEP_ALIVE=2m
COPY backend/requirements.txt backend/requirements-llm.txt ./
COPY --from=llama /wheels /wheels
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir /wheels/*.whl \
 && rm -rf /wheels
# libgomp: OpenMP runtime the llama.cpp CPU wheel links against.
# patchelf: same execstack fix for the native inference libraries.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libvulkan1 libopenblas0 patchelf \
 && find /usr/local/lib/python3.11/site-packages -name '*.so*' \( -path '*ctranslate2*' -o -path '*llama_cpp*' \) \
      -exec patchelf --clear-execstack {} + \
 && apt-get purge -y patchelf && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
RUN python -c "from llama_cpp import Llama"
COPY backend/ ./
COPY --from=model /m/models ./models
COPY --from=frontend /fe/out ./static
COPY --from=ollama-dist /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama-dist /usr/lib/ollama /usr/lib/ollama
COPY --from=ollama-model /opt/ollama/models /opt/ollama/models
EXPOSE 7860
CMD ["python", "ollama_service.py"]
