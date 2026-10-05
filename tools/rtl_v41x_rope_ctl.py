#!/usr/bin/env python3
"""Bounded full-shape core test for blocking RoPE prefetch and SU-drained release."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402
import rtl_hdc_v41x_decode_campaign as C  # noqa: E402

TB = ROOT / "rtl/test/tb_hdc_v41x_rope_ctl.sv"
OUT = ROOT / "results/rtl/v41x_rope_ctl.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cap() -> None:
    n = 24 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (n, n))


def main() -> None:
    program = [I.encode(full_shape=True, unit=I.UNIT_CTL, ctl=c, ctl_slot=0, ctl_lane=0)
               for c in (5, 6, I.CTL_END)]
    with tempfile.TemporaryDirectory(prefix="v41_rope_ctl_") as td:
        temp = Path(td)
        program_path = temp / "program.hex"
        program_path.write_text("".join(f"{word:0512x}\n" for word in program))
        program_sha = sha(program_path)
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        sources = list(C.rtl_sources(False)) + [
            ROOT / "rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv", TB]
        cmd = [verilator, "--binary", "--timing", "-O0", "-Wno-fatal", "-Wno-TIMESCALEMOD",
               "-Wno-PINMISSING", "--top-module", "tb_hdc_v41x_rope_ctl", "-Mdir", str(temp / "obj"),
               f"-I{C.SVH.parent}", *map(str, sources), "-CFLAGS", "-O0", "-j", "4"]
        build = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True,
                               timeout=300, preexec_fn=cap)
        if build.returncode:
            raise RuntimeError("build failed:\n" + build.stderr[-4000:])
        sim = subprocess.run([str(temp / "obj/Vtb_hdc_v41x_rope_ctl"), f"+PROG={program_path}"],
                             cwd=ROOT, text=True, capture_output=True,
                             timeout=60, preexec_fn=cap)
        match = re.search(r"ROPE_CTL_PASS requests=(\d+) releases=(\d+) cycles=(\d+)",sim.stdout)
        if sim.returncode or not match:
            raise RuntimeError("sim failed:\n" + sim.stdout[-3000:] + sim.stderr[-1000:])
    req, rel, cycles = map(int, match.groups())
    if (req,rel)!=(1,1):
        raise AssertionError((req,rel))
    record = {
        "schema": "opentallas.rtl.v41x_rope_ctl.v1", "status": "pass",
        "claim_scope": "Full-width core sequencer CTL5/6 ordering and DYN position for one position with computation units disabled; no SU arithmetic, die arbiter, or full-layer claim.",
        "requests": req, "releases": rel, "simulation_cycles": cycles,
        "memory_cap_bytes": 24*1024**3,
        "program_sha256": program_sha,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          (ROOT/"rtl/hdc/v41x/ot_hdc_core_v41x.sv", TB, Path(__file__),
                           ROOT/"tools/hdc_isa_v41.py", ROOT/"rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh")},
    }
    OUT.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({"status":record["status"],"cycles":cycles}))


if __name__ == "__main__":
    main()
