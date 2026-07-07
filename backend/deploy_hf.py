"""Deploy this repo to a HuggingFace Space (Docker SDK).

Usage:
    HF_TOKEN=hf_xxx SPACE_ID=<user>/nllb-translator python deploy_hf.py

Creates the Space if needed, uploads the repo (excluding heavy/ignored dirs),
and writes a Space README with the required Docker-Space frontmatter.
"""

from __future__ import annotations

import os
import sys

from huggingface_hub import HfApi

TOKEN = os.environ.get("HF_TOKEN")
if not TOKEN:
    sys.exit("Set HF_TOKEN (a write token from https://huggingface.co/settings/tokens)")

api = HfApi(token=TOKEN)
user = api.whoami()["name"]
space_id = os.environ.get("SPACE_ID", f"{user}/nllb-translator")
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FRONTMATTER = """---
title: NLLB Translator
emoji: 🌐
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

"""

IGNORE = [
    ".git/**", "_reference/**", "**/__pycache__/**",
    "backend/.venv/**", "backend/models/**",
    "frontend/node_modules/**", "frontend/.next/**", "frontend/out/**",
    "**/*.pyc",
]

print(f"Deploying to Space: {space_id}")
api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True)

# Upload the repo tree (skip README — replaced below with a frontmatter version).
api.upload_folder(
    folder_path=repo_root,
    repo_id=space_id,
    repo_type="space",
    ignore_patterns=IGNORE + ["README.md"],
    commit_message="Deploy multi-engine NLLB translator",
)

with open(os.path.join(repo_root, "README.md"), encoding="utf-8") as f:
    readme = FRONTMATTER + f.read()
api.upload_file(
    path_or_fileobj=readme.encode("utf-8"),
    path_in_repo="README.md",
    repo_id=space_id,
    repo_type="space",
    commit_message="Add Space frontmatter",
)

print(f"\nDone → https://huggingface.co/spaces/{space_id}")
print("The Space will build the Docker image (downloads + converts the model, ~2.4 GB).")
print("Add GEMINI_API_KEY / GROQ_API_KEY as Space secrets to enable the cloud engines.")
