"""CPU limits for local inference inside containers and normal installations."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Lock


LOCAL_INFERENCE_LOCK = Lock()


def check_cancelled(cancel: Event | None = None) -> None:
    if cancel is not None and cancel.is_set():
        raise InterruptedError("Translation cancelled.")


@contextmanager
def local_inference(cancel: Event | None = None):
    """Give CPU models one inference slot; canceled waiters never start work."""
    check_cancelled(cancel)
    while not LOCAL_INFERENCE_LOCK.acquire(timeout=0.1):
        check_cancelled(cancel)
    try:
        check_cancelled(cancel)
        yield
    finally:
        LOCAL_INFERENCE_LOCK.release()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return ""


def _quota_limits() -> list[int]:
    """Read cgroup v2/v1 quotas; root paths also work in cgroup namespaces."""
    root = Path("/sys/fs/cgroup")
    v2_paths = {root}
    v1_paths = {root / "cpu", root / "cpu,cpuacct", root}
    for line in _read(Path("/proc/self/cgroup")).splitlines():
        fields = line.split(":", 2)
        if len(fields) != 3:
            continue
        _, controllers, group = fields
        # A namespaced path can contain '..'; the namespace root is already probed.
        relative = Path(group.lstrip("/"))
        if ".." in relative.parts:
            continue
        if not controllers:
            current = root / relative
            while current != root:
                v2_paths.add(current)
                current = current.parent
        elif "cpu" in controllers.split(","):
            for mount in (root / "cpu", root / "cpu,cpuacct"):
                current = mount / relative
                while current != mount:
                    v1_paths.add(current)
                    current = current.parent

    limits = []
    for path in v2_paths:
        values = _read(path / "cpu.max").split()
        if len(values) == 2 and values[0] != "max":
            try:
                quota, period = map(int, values)
                if quota > 0 and period > 0:
                    limits.append(max(1, quota // period))
            except ValueError:
                pass
    for path in v1_paths:
        try:
            quota = int(_read(path / "cpu.cfs_quota_us"))
            period = int(_read(path / "cpu.cfs_period_us"))
            if quota > 0 and period > 0:
                limits.append(max(1, quota // period))
        except ValueError:
            pass
    return limits


def cpu_thread_count(override: int | None = 0) -> int:
    """Honor an explicit setting, otherwise respect affinity and CPU quotas.

    os.cpu_count() alone often reports the entire HF host even when a Space only
    has two CPUs. Large inference thread pools then spend time being throttled.
    """
    if override and override > 0:
        return override
    limits = [os.cpu_count() or 1]
    try:
        limits.append(len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    limits.extend(_quota_limits())
    return max(1, min(limits))
