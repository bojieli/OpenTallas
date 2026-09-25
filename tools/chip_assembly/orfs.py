"""OpenROAD-flow-scripts driver shared by every hierarchy level.

One *case* is one ORFS design: a work directory holding ``config.mk``, the
SDC, hook Tcl, and any macro views, mounted at ``/work`` in the pinned
``openroad/orfs`` container with the repository mounted read-only at
``/src``.  ORFS's make is incremental, so re-running a goal on a kept case
resumes where a timeout or a kill left it instead of restarting.

The machine is shared: a run takes one of ``OT_CHIP_SLOTS`` (default 2)
slots, held by an exclusive lock on a file under ``OT_CHIP_SLOT_DIR``, and
starts only when ``MemAvailable`` is at least ``OT_CHIP_MIN_MEM_GB`` (default
60 GB).
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
ORFS_IMAGE = os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest")
PLATFORM = "asap7"
SLOT_DIR = Path(os.environ.get("OT_CHIP_SLOT_DIR", "/tmp/claude-1000/ot_chip_slots"))
SLOTS = int(os.environ.get("OT_CHIP_SLOTS", "2"))
MIN_MEM_GB = float(os.environ.get("OT_CHIP_MIN_MEM_GB", "60"))
_SIGNED_RE = re.compile(r"^(\s*(?:input|output|inout|wire|reg)\s+)signed\s+", re.M)


class FlowError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mem_available_gb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    return 0.0


@contextlib.contextmanager
def slot(label: str, poll_seconds: int = 60) -> Iterator[int]:
    """Hold one of SLOTS run slots, and wait for memory before starting."""
    SLOT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        for index in range(SLOTS):
            handle = open(SLOT_DIR / f"slot{index}.lock", "a+")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                continue
            try:
                while mem_available_gb() < MIN_MEM_GB:
                    time.sleep(poll_seconds)
                handle.seek(0)
                handle.truncate()
                handle.write(f"{label} pid={os.getpid()} since={time.time():.0f}\n")
                handle.flush()
                yield index
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
                handle.close()
            return
        time.sleep(poll_seconds)


def docker_make(case: Path, goal: str, log_name: str, timeout: int,
                extra_mounts: list[tuple[Path, str]] | None = None,
                env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    cmd = ["docker", "run", "--rm", "-v", f"{ROOT}:/src:ro", "-v", f"{case}:/work"]
    for host, container in extra_mounts or []:
        cmd += ["-v", f"{host}:{container}:ro"]
    for key, value in (env or {}).items():
        cmd += ["-e", f"{key}={value}"]
    cmd += [
        "-w", "/OpenROAD-flow-scripts/flow", ORFS_IMAGE, "bash", "-lc",
        "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; "
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
        f"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base {goal}",
    ]
    with (case / log_name).open("a", encoding="utf-8") as log:
        log.write(f"\n### {time.strftime('%Y-%m-%dT%H:%M:%S')} make {goal}\n")
        log.flush()
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                              check=False, text=True)
    return proc


def docker_openroad(case: Path, script: str, log_name: str, timeout: int = 7200,
                    extra_mounts: list[tuple[Path, str]] | None = None) -> subprocess.CompletedProcess:
    """Run an OpenROAD Tcl script (path inside /work) in the container."""
    cmd = ["docker", "run", "--rm", "-v", f"{ROOT}:/src:ro", "-v", f"{case}:/work"]
    for host, container in extra_mounts or []:
        cmd += ["-v", f"{host}:{container}:ro"]
    cmd += [
        "-w", "/work", ORFS_IMAGE, "bash", "-lc",
        "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; "
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
        f"openroad -no_init -exit {script}",
    ]
    with (case / log_name).open("w", encoding="utf-8") as log:
        return subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                              check=False, text=True)


def normalise_netlist(path: Path) -> int:
    """Strip ``signed`` from declarations (OpenROAD's reader rejects it)."""
    text = path.read_text(encoding="utf-8")
    out, count = _SIGNED_RE.subn(r"\1", text)
    if count:
        path.write_text(out, encoding="utf-8")
    return count


def results_dir(case: Path, nickname: str) -> Path:
    return case / "results" / PLATFORM / nickname / "base"


def reports_dir(case: Path, nickname: str) -> Path:
    return case / "reports" / PLATFORM / nickname / "base"


def logs_dir(case: Path, nickname: str) -> Path:
    return case / "logs" / PLATFORM / nickname / "base"


def orfs_identity() -> dict[str, Any]:
    proc = subprocess.run(["docker", "image", "inspect", ORFS_IMAGE, "--format", "{{.Id}}"],
                          capture_output=True, text=True, check=False)
    return {"image": ORFS_IMAGE, "image_id": (proc.stdout or "").strip()}


def git_identity() -> dict[str, Any]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                            text=True, check=False)
    dirt = [line for line in (status.stdout or "").splitlines()
            if line.strip() and not line[3:].startswith("results/")]
    return {"commit": (head.stdout or "").strip() or None, "worktree_dirty": bool(dirt),
            "worktree_status": dirt[:50]}


def source_digests(sources: list[str]) -> list[dict[str, Any]]:
    return [{"path": s, "sha256": sha256_file(ROOT / s)} for s in sources]


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
