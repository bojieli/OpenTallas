#!/usr/bin/env python3
"""Emit exact plain-RoPE CROM words for one full-shape token position."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402

CONFIG = ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json"
OUTDIR = ROOT / "results/rtl"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(layout_path: Path) -> dict:
    config = json.loads(CONFIG.read_text())
    layout = json.loads(layout_path.read_text())
    constants = layout["constants"]
    base = max(e["base_word"] + e["word_count"] for e in constants.values())
    rd = config["rope_head_dim"]
    if rd != 64 or base >= (1 << 30):
        raise ValueError("unexpected V4.1 RoPE or CROM geometry")
    freqs = V.rope_freqs(rd, 0, config["rope_theta"], config["rope_factor"],
                         config["beta_fast"], config["beta_slow"])
    positions = {}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for context in (200_000, 1_048_576):
        pos = context - 1
        cos, sin = V.rope_cs(freqs, pos)
        pairs = np.stack((cos, sin), axis=-1).astype("<f4")
        if pairs.shape != (32, 2) or not np.all(np.isfinite(pairs)):
            raise ValueError("bad plain RoPE values")
        path = OUTDIR / f"v41_rope_plain_ctx{context}_token_patch.bin"
        path.write_bytes(pairs.tobytes())
        positions[str(context)] = {
            "position": pos,
            "crom_word_base": base,
            "crom_absolute_first_word": base + pos * 32,
            "crom_absolute_last_word": base + pos * 32 + 31,
            "file": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha(path),
        }
    return {
        "schema": "opentallas.rtl.v41_fullshape_rope_sparse_patch.v1",
        "status": "exact_input_only",
        "claim_boundary": "Two 256-byte token-position plain-RoPE patches for full-shape RTL input. "
                          "These sparse patches do not provide a production 1M-position CROM, "
                          "HBM prefetch, timing, or die capacity solution.",
        "format": "32 adjacent (cos FP32, sin FP32) CROM pairs per position, little-endian",
        "contexts": positions,
        "source_sha256": {
            str(CONFIG.relative_to(ROOT)): sha(CONFIG),
            "tools/hdc_golden_v41.py": sha(ROOT / "tools/hdc_golden_v41.py"),
            "tools/hdc_replay_v41.py": sha(ROOT / "tools/hdc_replay_v41.py"),
            "tools/v41_fullshape_rope_sparse_patch.py": sha(Path(__file__)),
            "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json": sha(layout_path),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", required=True, type=Path)
    ap.add_argument("--output", type=Path,
                    default=OUTDIR / "hdc_v41x_fullshape_rope_sparse_patch.json")
    args = ap.parse_args()
    record = generate(args.layout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
