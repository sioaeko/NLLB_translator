FROM python:3.11-slim

WORKDIR /app

# System deps for sentencepiece / protobuf builds are already wheels; keep slim.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Convert the model at build time so the image ships ready-to-serve.
# (Comment out to convert on first run instead and keep the image small.)
RUN python convert_model.py

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
