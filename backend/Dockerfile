# Backend-only image (used by docker-compose and split deployments).
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-convert.txt requirements-llm.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r requirements-llm.txt \
      --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu --only-binary=llama-cpp-python \
 && pip install --no-cache-dir -r requirements-convert.txt --extra-index-url https://download.pytorch.org/whl/cpu
# libgomp: OpenMP runtime for the llama.cpp CPU wheel. patchelf clears the
# executable-stack flag some hardened container runtimes refuse.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 patchelf \
 && find /usr/local/lib/python3.11/site-packages -name '*.so*' \( -path '*ctranslate2*' -o -path '*llama_cpp*' \) \
      -exec patchelf --clear-execstack {} + \
 && apt-get purge -y patchelf && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY . .

# Prepare both local models at build time so the image ships ready to serve.
RUN python convert_model.py && python fetch_hymt.py

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
