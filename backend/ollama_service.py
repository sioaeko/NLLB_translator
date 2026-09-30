"""Prepare or supervise the bundled Ollama server in the Space container."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from threading import Event
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen


def model_present(payload: dict, model: str) -> bool:
    def normalized(name: str) -> str:
        return name if ":" in name.rsplit("/", 1)[-1] else name + ":latest"

    return any(
        normalized(item.get("name", item.get("model", ""))) == normalized(model)
        for item in payload.get("models", [])
        if isinstance(item, dict)
    )


def read_models(host: str) -> dict:
    with urlopen(host.rstrip("/") + "/api/tags", timeout=2) as response:
        return json.load(response)


def spawn(command: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def wait_ready(process: subprocess.Popen, host: str, stop: Event) -> None:
    deadline = time.monotonic() + 60
    while not stop.is_set():
        if process.poll() is not None:
            raise RuntimeError("Ollama exited before it became ready")
        try:
            read_models(host)
            return
        except (URLError, TimeoutError, ValueError, OSError):
            if time.monotonic() >= deadline:
                raise RuntimeError("Ollama did not become ready within 60 seconds")
            stop.wait(0.5)
    raise InterruptedError("Container shutdown requested")


def supervise(children: list[subprocess.Popen], stop: Event) -> int:
    while not stop.wait(0.5):
        for child in children:
            code = child.poll()
            if code is not None:
                print(f"Container service exited (status {code})", flush=True)
                return code or 1
    return 0


def main() -> int:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    if "://" not in host:
        host = "http://" + host
    if urlparse(host).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The bundled Ollama server must bind to a loopback address")
    os.environ["OLLAMA_HOST"] = host
    model = os.environ.get("OLLAMA_MODEL", "translategemma:4b")
    stop = Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    children = []
    try:
        server = spawn(["ollama", "serve"])
        children.append(server)
        wait_ready(server, host, stop)
        if "--pull" in sys.argv[1:]:
            pull = spawn(["ollama", "pull", model])
            children.append(pull)
            deadline = time.monotonic() + 1800
            while pull.poll() is None:
                if stop.wait(0.5):
                    raise InterruptedError("Model download interrupted")
                if server.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("Ollama model download failed or timed out")
            if pull.returncode:
                raise RuntimeError(f"Ollama pull failed (status {pull.returncode})")
        if not model_present(read_models(host), model):
            raise RuntimeError(f"The bundled Ollama model is missing: {model}")
        print(f"Ollama model ready: {model}", flush=True)
        if "--pull" in sys.argv[1:]:
            return 0
        children.append(spawn([
            sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0",
            "--port", os.environ.get("PORT", "7860"),
        ]))
        return supervise(children, stop)
    except InterruptedError:
        return 0
    finally:
        for child in reversed(children):
            stop_process(child)


if __name__ == "__main__":
    sys.exit(main())
