#!/usr/bin/env python3
"""Exact real-coefficient and shared-port backpressure gate for V4.1 RoPE cache."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402

RTL = ROOT / "rtl/chip/ot_chip_v41x_rope_hbm_cache.sv"
TB = ROOT / "rtl/test/tb_chip_v41x_rope_hbm_cache.sv"
CONFIG = ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json"
OUT = ROOT / "results/rtl/v41x_rope_hbm_cache.json"
PAT = re.compile(r"ROPE_HBM_PASS fills=(\d+) sectors=(\d+) hits=(\d+) stalls=(\d+) reordered=(\d+) cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cap() -> None:
    lim = 8 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (lim, lim))


def emit_fixture(temp: Path) -> dict:
    c = json.loads(CONFIG.read_text())
    rd = c["rope_head_dim"]
    if rd != 64:
        raise ValueError("unexpected RoPE head dimension")
    cases = {"plain200k": (False, 199999), "plain1m": (False, 1048575),
             "yarn200k": (True, 199999)}
    hashes = {}
    for name, (yarn, pos) in cases.items():
        f = V.rope_freqs(rd, c["original_seq_len"] if yarn else 0,
                         c["compress_rope_theta"] if yarn else c["rope_theta"],
                         c["rope_factor"], c["beta_fast"], c["beta_slow"])
        cs, sn = V.rope_cs(f, pos)
        pairs = np.stack((cs, sn), axis=-1).astype("<f4")
        if pairs.shape != (32, 2) or not np.all(np.isfinite(pairs)):
            raise ValueError("bad RoPE coefficient fixture")
        words = np.frombuffer(pairs.tobytes(), dtype="<u8")
        path = temp / f"{name}.hex"
        path.write_text("".join(f"{int(w):016x}\n" for w in words))
        hashes[name] = {"position": pos, "kind": "yarn" if yarn else "plain",
                        "binary_sha256": hashlib.sha256(pairs.tobytes()).hexdigest(),
                        "hex_sha256": sha(path)}
    if hashes["plain200k"]["binary_sha256"] != "9745343dc1b7a72ee053530588f7a0df5c3e42c1f2587afbf64909946030eeb8":
        raise ValueError("plain 200K coefficients changed relative to exact shard patch")
    return hashes


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="v41_rope_hbm_") as td:
        temp = Path(td)
        fixtures = emit_fixture(temp)
        obj = temp / "obj"
        verilator = str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator")
        cmd = [verilator, "--binary", "--timing", "-O0", "-Wno-fatal", "-Wno-TIMESCALEMOD",
               "--top-module", "tb_chip_v41x_rope_hbm_cache", "-Mdir", str(obj),
               str(RTL), str(TB), "-CFLAGS", "-O0", "-j", "4"]
        start = time.monotonic()
        build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               timeout=300, preexec_fn=cap)
        if build.returncode:
            raise RuntimeError("RoPE cache build failed:\n" + build.stderr[-3000:])
        build_s = round(time.monotonic() - start, 2)
        sim = subprocess.run([str(obj / "Vtb_chip_v41x_rope_hbm_cache"), f"+DIR={temp}"],
                             cwd=ROOT, capture_output=True, text=True,
                             timeout=60, preexec_fn=cap)
        match = PAT.search(sim.stdout)
        if sim.returncode or not match:
            raise RuntimeError("RoPE cache sim failed:\n" + sim.stdout[-3000:] + sim.stderr[-2000:])
        fills, sectors, hits, stalls, reordered, cycles = map(int, match.groups())
        if (fills, sectors, hits) != (3, 24, 1) or stalls < 1 or reordered < 1:
            raise RuntimeError("RoPE cache coverage mismatch: " + match.group(0))
        record = {
            "schema": "opentallas.rtl.v41x_rope_hbm_cache.v1", "status": "pass",
            "claim_scope": "Standalone four-stack 256-bit K-port RoPE sector client, exact "
                           "200K plain/YaRN and 1M plain FP32 coefficients, cache hold/release, "
                           "backpressure and reordered tagged replies. Not integrated with the "
                           "die arbiter, RTL SU CROM mux, HBM PHY, or a routed physical view.",
            "fills": fills, "sectors_received": sectors, "cache_hits": hits,
            "stalled_cycles": stalls, "reordered_responses": reordered,
            "simulation_cycles": cycles, "build_seconds": build_s,
            "memory_cap_bytes": 8 * 1024**3, "fixtures": fixtures,
            "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                              (RTL, TB, CONFIG, ROOT / "tools/hdc_golden_v41.py", Path(__file__))},
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
