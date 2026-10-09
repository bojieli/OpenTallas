#!/usr/bin/env python3
"""CF-QDQ vectors from the released DS arithmetic; lane zero is packed LSB.

Each input line is 32 FP32 lanes (1024 bits), each output line is 32 BF16
lanes (512 bits). No alternate implementation of the quantiser is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import hdc_golden_v41 as G


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases(block, seed):
    rng = np.random.default_rng(seed)
    rows = []
    def add(name, values):
        rows.append((name, np.resize(np.asarray(values, dtype=np.float32), 32)))
    add("zero", [0.0])
    add("signed_zero", G.from_bits([0, 0x80000000]))
    add("fp32_subnormals", G.from_bits([1, 2, 0x400000, 0x7fffff, 0x80000001, 0x807fffff]))
    add("bf16_subnormals", G.from_bits([0x10000, 0x20000, 0x7f0000, 0x80010000]))
    add("minimum_normal", G.from_bits([0x800000, 0x80800000]))
    add("maximum_finite", G.from_bits([0x7f7fffff, 0xff7fffff]))
    add("e4m3_scale_saturation", [2688.0, 2689.0, 4096.0, -4096.0, 1.0])
    # Anchors fix the quantisation scale; exact midpoint and adjacent FP32
    # values distinguish ties-to-even from truncation and ties-away rounding.
    for exponent in [-20, -8, 0, 8, 40]:
        for kind, anchors, mids in [
            ("fp8", 448.0, [0.0009765625, 0.0029296875, 1.0625, 1.1875, 3.125]),
            ("fp4", 6.0, [0.25, 0.75, 1.25, 1.75, 2.5, 3.5, 5.0]),
        ]:
            values = [np.float32(anchors * 2.0**exponent)]
            for midpoint in mids:
                m = np.float32(midpoint * 2.0**exponent)
                values.extend([np.nextafter(m, np.float32(-np.inf)), m,
                               np.nextafter(m, np.float32(np.inf)), -m])
            beat = np.resize(np.asarray(values, dtype=np.float32), 32)
            for start in range(0, 32, block):
                beat[start] = values[0]
            rows.append((f"{kind}_ties_exp{exponent}", beat))
    if block == 16:
        # The two independent halves must not share their maximum/scale.
        rows.append(("independent_half_scales", np.concatenate([
            np.linspace(-0.01, 0.01, 16, dtype=np.float32),
            np.linspace(-1536, 1536, 16, dtype=np.float32)])))
    for i in range(32):
        exponent = int(rng.integers(-120, 110))
        values = np.ldexp(rng.uniform(-1, 1, 32).astype(np.float32), exponent)
        rows.append((f"random_{i}_exp{exponent}", values))
    return rows


def packed(values, width):
    return "".join(f"{int(x):0{width // 4}x}" for x in reversed(values))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=20261009)
    p.add_argument("--source-commit", help="Pinned git-archive commit for a minimal remote bundle")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    manifest = {"schema": "CF-QDQ-v1", "lane_order": "lane0_lsb",
                "input": "32xFP32/1024b", "output": "32xBF16/512b",
                "seed": args.seed, "numpy": np.__version__,
                "python": platform.python_version(), "modes": {},
                "source_commit": args.source_commit or subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "sources": {str(f.relative_to(root)): sha(f) for f in [
                    Path(__file__).resolve(), root / "tools/hdc_golden_v41.py",
                    root / "tools/hdc_golden.py"]}}
    modes = [("fp8_e8m0", 4, 32, G.qdq_fp8),
             ("fp4_e8m0", 5, 32, G.qdq_fp4_e8m0),
             ("fp4_e4m3", 6, 16, G.qdq_fp4_e4m3)]
    for name, op, block, golden in modes:
        rows = cases(block, args.seed)
        inputs, outputs = [], []
        for label, x in rows:
            with np.errstate(over="ignore", under="ignore", invalid="raise"):
                y = golden(x, block=block)
            inputs.append(packed(G.bits(x), 32))
            outputs.append(packed(G.bits(y) >> 16, 16))
        for suffix, lines in [("in", inputs), ("out", outputs)]:
            (args.out / f"{name}.{suffix}.hex").write_text("\n".join(lines) + "\n")
        manifest["modes"][name] = {"op": op, "block": block, "beats": len(rows),
            "cases": [label for label, _ in rows],
            "files": {f"{name}.{s}.hex": sha(args.out / f"{name}.{s}.hex")
                      for s in ["in", "out"]}}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "modes": {
        k: v["beats"] for k, v in manifest["modes"].items()}}))


if __name__ == "__main__":
    main()
