#!/usr/bin/env python3
"""Source-pinned full-shape RoPE values for exact-token shard simulation.

This is an oracle for the on-read angle generator.  It does not place a
1M-position CROM table or establish the generator's RTL implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(position: int, config_path: Path) -> dict:
    if not 0 <= position < 1 << 21:
        raise ValueError("position outside full-shape PW21")
    config = json.loads(config_path.read_text())
    rd = int(config["rope_head_dim"])
    if rd != 64:
        raise ValueError("expected full-shape 64-D RoPE tail")
    modes = {}
    for name, original, theta in (
        ("plain", 0, config["rope_theta"]),
        ("yarn", config["original_seq_len"], config["compress_rope_theta"]),
    ):
        freqs = V.rope_freqs(rd, original, theta, config["rope_factor"],
                             config["beta_fast"], config["beta_slow"])
        cos, sin = V.rope_cs(freqs, position)
        angles = (np.float32(position) * freqs).astype(np.float32)
        independent_cos = np.array([math.cos(float(a)) for a in angles], dtype=np.float32)
        independent_sin = np.array([math.sin(float(a)) for a in angles], dtype=np.float32)
        if not np.array_equal(cos.view(np.uint32), independent_cos.view(np.uint32)):
            raise AssertionError(f"{name}: independent cosine differs from golden")
        if not np.array_equal(sin.view(np.uint32), independent_sin.view(np.uint32)):
            raise AssertionError(f"{name}: independent sine differs from golden")
        # Layout.put stores one 64-bit CROM word per frequency: low cos, high sin.
        pairs = np.column_stack((cos.view(np.uint32), sin.view(np.uint32))).astype("<u4")
        modes[name] = {
            "freq_count": rd // 2,
            "angle_fp32_bits": [f"{int(x):08x}" for x in angles.view(np.uint32)],
            "crom_pair_words_hex": [f"{int(h):08x}{int(l):08x}" for l, h in pairs],
            "pair_bytes_sha256": hashlib.sha256(pairs.tobytes()).hexdigest(),
            "independent_math_ulp_mismatches": 0,
        }
    return {
        "schema": "opentallas.v41x.fullshape.rope_oracle.v1",
        "status": "one_position_oracle_exact",
        "claim_boundary": "Golden and independent binary32 sin/cos agree for this position; no RoPE RTL, on-read generator, or full CROM table is implemented by this record.",
        "position": position,
        "config_path": str(config_path.relative_to(ROOT)),
        "config_sha256": digest(config_path),
        "golden_sha256": digest(ROOT / "tools/hdc_golden_v41.py"),
        "tool_sha256": digest(Path(__file__)),
        "modes": modes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--position", type=int, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    record = build(a.position, ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=2) + "\n")
    print(f"RoPE oracle pos {a.position}: {len(record['modes'])} modes × 32 pairs, exact")


if __name__ == "__main__":
    main()
