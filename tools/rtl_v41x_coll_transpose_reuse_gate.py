#!/usr/bin/env python3
"""Source-pinned exact back-to-back descriptor gate for the GW4 output pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = Path("/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator")
SOURCES = [
    "rtl/chip/ot_chip_v41x_coll_transpose.sv",
    "rtl/test/tb_v41x_coll_transpose_reuse.sv",
    "tools/rtl_v41x_coll_transpose_reuse_gate.py",
]
OUT = ROOT / "results/rtl/v41x_coll_transpose_reuse.json"


def run(scratch: Path) -> dict:
    scratch.mkdir(parents=True, exist_ok=True)
    top = "tb_v41x_coll_transpose_reuse"
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "4", "-Wno-fatal",
           "-Wno-TIMESCALEMOD", "--top-module", top, "--Mdir", str(scratch),
           *[str(ROOT / p) for p in SOURCES[:2]]]
    build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        raise RuntimeError(build.stderr[-4000:])
    sim = subprocess.run([str(scratch / f"V{top}")], cwd=ROOT, capture_output=True, text=True)
    if sim.returncode:
        raise RuntimeError(sim.stdout[-2000:] + sim.stderr[-2000:])
    match = re.search(r"TRANSPOSE_REUSE_PASS ops=(\d+) writes=(\d+) lasts=(\d+) stalls=(\d+) cycles=(\d+)", sim.stdout)
    if not match:
        raise AssertionError(sim.stdout[-2000:])
    ops, writes, lasts, stalls, cycles = map(int, match.groups())
    assert (ops, writes, lasts) == (2, 1084, 2)
    assert stalls > 0
    return {
        "schema": "v41x_coll_transpose_reuse_v1",
        "verilator": subprocess.check_output([str(VERILATOR), "--version"], text=True).strip(),
        "scope": "two exact consecutive GW4 descriptors, 5 and 266 words per rank, registered always-ready bank sink; no die route claim",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "ops": ops, "writes": writes, "lasts": lasts, "input_stalls": stalls, "cycles": cycles,
        "passed": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    record = run(args.scratch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
