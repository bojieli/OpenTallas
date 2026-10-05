#!/usr/bin/env python3
"""Measure real TP-4 sequencers and collective on a 4096-element vector.

This excludes the decode core and is complementary to the live layer-0 gate.
No production parameter, arithmetic, descriptor default or timing changes.
"""
import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import hdc_golden as G

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["rtl/rom/ot_qwen_tp_seq_w12.sv", "rtl/rom/ot_rom_oneshot_allreduce.sv",
           "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/test/tb_qwen_tp4_ar256.sv",
           "tools/hdc_golden.py", "tools/qwen_tp4_ar256_gate.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    args = ap.parse_args()
    if args.result.exists():
        raise SystemExit("Refusing to overwrite an existing verdict")
    args.work.mkdir(parents=True, exist_ok=False)
    pins = {p: sha(ROOT / p) for p in SOURCES}
    rng = np.random.default_rng(20261001)
    parts = rng.uniform(-4, 4, (4, 256, 16)).astype(np.float32)
    # Deliberately distinguish rank-order addition from a balanced tree.
    parts[:, 0, 0] = np.array([2**24, 1, -(2**24), 1], dtype=np.float32)
    parts[:, 0, 1] = np.array([0.0, -0.0, 0.0, -0.0], dtype=np.float32)
    expected = G.bits(G.fold(parts))
    assert int(expected[0, 0]) == 0x3f800000

    def emit(path, array):
        path.write_text("".join("".join(f"{int(v):08x}" for v in row[::-1]) + "\n" for row in array))

    for d in range(4):
        emit(args.work / f"part_die{d}.hex", G.bits(parts[d]))
    emit(args.work / "sum.hex", expected)
    runs = {}
    binary = args.work / "gate.vvp"

    def run(name, cmd, limit):
        t0 = time.monotonic()
        p = subprocess.run(list(map(str, cmd)), cwd=ROOT, capture_output=True, text=True, timeout=limit)
        log = args.work / f"{name}.log"
        log.write_text(p.stdout + p.stderr)
        runs[name] = {"returncode": p.returncode, "wall_seconds": round(time.monotonic()-t0, 3),
                      "log_sha256": sha(log), "command": list(map(str, cmd))}
        if p.returncode:
            raise RuntimeError(f"{name} failed: {p.stdout[-1000:]} {p.stderr[-1000:]}")
        return p.stdout

    result = {"schema": "opentallas.qwen-tp4-ar256-gate.v1", "status": "fail",
              "source_sha256": pins, "runs": runs, "cases": {},
              "design_point": {"tp": 4, "lanes": 16, "elements": 4096, "lat": 339, "depth": 1024},
              "claim_boundary": "Real sequencer, VM word ports, rank-order FP32 collective and links; stub core handshake. No full-layer/token claim or SS/FF sign-off; opt-in production setting remains unchanged."}
    try:
        run("compile", ["iverilog", "-g2012", "-s", "tb_qwen_tp4_ar256", "-o", binary,
                        *(ROOT / p for p in SOURCES[:4])], 600)
        for name, split, inject in [("split128", 1, 0), ("one256", 0, 0), ("bad_last", 0, 1)]:
            stdout = run(name, ["vvp", binary, f"+VEC={args.work}", f"+SPLIT={split}",
                                f"+INJECT_LAST={inject}"], 600)
            m = re.search(r"QWEN_AR256 PASS .*cycles=(\d+) words=1024 lanes=16384 mismatches=0 seq_fault=([01]+) stalls=(\d+)", stdout)
            if not m:
                raise RuntimeError(f"{name}: missing complete gate verdict")
            result["cases"][name] = {"cycles": int(m[1]), "seq_fault": m[2], "link_stalls": int(m[3])}
        result["cycles_saved_per_vector"] = result["cases"]["split128"]["cycles"] - result["cases"]["one256"]["cycles"]
        result["source_stable"] = pins == {p: sha(ROOT / p) for p in SOURCES}
        if not result["source_stable"] or result["cycles_saved_per_vector"] <= 0:
            raise RuntimeError("Source instability or no measured cycle gain")
        result["status"] = "pass"
    except Exception as exc:
        result["error"] = str(exc)
    result["vector_sha256"] = {p.name: sha(p) for p in args.work.glob("*.hex")}
    args.result.parent.mkdir(parents=True, exist_ok=True)
    with args.result.open("x") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "cases": result["cases"],
                      "cycles_saved": result.get("cycles_saved_per_vector"), "error": result.get("error")}, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
