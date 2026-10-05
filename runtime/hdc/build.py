"""Build products of the runtime: the Verilated chip and the model's images.

Both are cached under ``build/hdc_host/`` keyed by the hash of what produced
them, so a changed RTL file or image generator rebuilds, and an unchanged one
is reused across processes.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from runtime.hdc.targets import ROOT, Target

CACHE = ROOT / "build/hdc_host"
HARNESS = "rtl/test/host_bridge_harness.cpp"
INCLUDES = ("rtl/test/tb_host_ports.svh", "rtl/test/tb_host_conn.svh", "rtl/hdc/ot_hdc_isa.svh",
            "rtl/hdc/v41/ot_hdc_isa_v41.svh")
IMAGE_TOOLS = {
    "qwen3": ("tools/hdc_program.py", "tools/hdc_golden.py", "tools/hdc_isa.py"),
    "qwen3-array": ("tools/hdc_program.py", "tools/hdc_golden.py", "tools/hdc_isa.py"),
    "v41": ("tools/hdc_program_v41.py", "tools/hdc_golden.py", "tools/hdc_golden_v41.py", "tools/hdc_isa_v41.py"),
}


def _digest(paths, extra: str = "") -> str:
    h = hashlib.sha256(extra.encode())
    for rel in paths:
        h.update(rel.encode())
        h.update((ROOT / rel).read_bytes())
    return h.hexdigest()[:16]


def _locked_build(final: Path, make) -> Path:
    """Run ``make(tmpdir)`` and move the result to ``final`` atomically."""
    if final.exists():
        return final
    final.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=final.name + ".", dir=final.parent))
    try:
        make(tmp)
        try:
            os.rename(tmp, final)
        except OSError:                      # another process won the race
            shutil.rmtree(tmp, ignore_errors=True)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return final


def build_chip(t: Target, jobs: int = 8) -> Path:
    """Verilate the target's top with the host bridge; returns the executable."""
    params = sorted(t.params.items())
    key = _digest(list(t.sources) + list(INCLUDES) + [HARNESS], repr((t.top, params, t.verilator_flags)))
    final = CACHE / f"chip-{t.name}-{key}"

    def make(d: Path):
        (d / "host_top.h").write_text(f'#include "V{t.top}.h"\n#define VTOP V{t.top}\n')
        cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
               "-Wno-BLKSEQ", *t.verilator_flags, "--top-module", t.top, "-Mdir", str(d / "obj"),
               f"-I{ROOT / 'rtl/test'}", f"-I{ROOT / 'rtl/hdc'}", f"-I{ROOT / 'rtl/hdc/v41'}",
               *[f"-G{k}={v}" for k, v in params],
               *[str(ROOT / s) for s in t.sources], str(ROOT / HARNESS),
               "-CFLAGS", f"-O1 -I{d}", "-j", str(jobs)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"verilator build of {t.top} failed:\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
    return _locked_build(final, make) / "obj" / f"V{t.top}"


def build_images(t: Target) -> Path:
    """Program/ROM images of the target's model (tools/hdc_program*.py)."""
    tools = IMAGE_TOOLS[t.images]
    extra = repr(sorted(t.params.items())) + os.environ.get("HDC_GROUPS", "")
    final = CACHE / f"images-{t.images}-{_digest(tools, extra)}"

    def make(d: Path):
        if t.images == "qwen3":
            cmd = [sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(d)]
        elif t.images == "v41":
            cmd = [sys.executable, str(ROOT / "tools/hdc_program_v41.py"), "--out", str(d)]
        else:                                 # layer-per-package array: one program per package
            cmd = [sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(d),
                   "--stages", str(t.params.get("NODES", 4))]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"image generation failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return _locked_build(final, make)
