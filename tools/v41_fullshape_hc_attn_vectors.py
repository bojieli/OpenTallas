#!/usr/bin/env python3
"""Capture checkpoint-backed V4.1 L0 hyper-connection attention matvec vectors.

Observes the original matvec_c(fn, flat, HC_SPLIT, cls="he") call. The full
layer output must still match the pinned golden shard before vectors are saved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

import rtl_v41_fullshape_layer_campaign as C

V = C.V  # campaign selects chunk8 before loading the golden
ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 200000


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(golden_dir: Path, output_dir: Path, record: Path, seed: int = C.SEED) -> dict:
    shard = json.loads((golden_dir / "ctx200000_L00.json").read_text())
    if (shard["context"], shard["layer"], shard["arith"]) != (CONTEXT, 0, "chunk8"):
        raise ValueError("wrong golden shard/arithmetic")
    ck = C.Checkpoint()
    m, init_pin = C.build_model(ck, engram=False)
    state, _ = C.synthetic_state(m, CONTEXT, seed=seed, layers=[0])
    history = C.token_history(CONTEXT, seed=seed)
    h = np.repeat(ck.rows("embed.weight", [history[-1]]), m.hc, axis=0).astype(np.float32)
    pre = np.array([1, 0, 0, 0], dtype=np.float32)[:m.hc]
    if C.digest(h, pre) != shard["input_sha256"]:
        raise ValueError("rerun input differs from pinned shard")
    context = {"pos": CONTEXT - 1, "hist": history, "h": h, "pre": pre}
    captures: list[tuple[np.ndarray, np.ndarray, tuple[int, ...], int]] = []
    original = V.matvec_c

    def observe(w, x, split, cls="me"):
        result = original(w, x, split, cls)
        if cls == "he":
            captures.append((np.asarray(x, dtype=np.float32).copy(),
                             np.asarray(result, dtype=np.float32).copy(), np.shape(w), split))
        return result

    V.matvec_c = observe
    try:
        m.layer(0, context, state, {})
    finally:
        V.matvec_c = original
    if C.digest(context["h"], context["pre"]) != shard["output_sha256"]:
        raise ValueError("rerun layer output differs from pinned shard")
    if len(captures) != 2:  # attention mix then FFN mix
        raise ValueError(f"expected two HE calls, got {len(captures)}")
    x, y, shape, split = captures[0]
    if (x.size, y.size, shape, split) != (20480, 24, (24, 20480), V.HC_SPLIT):
        raise ValueError("attention HE descriptor mismatch")
    if not np.array_equal(x, h.reshape(-1)) or np.any(x.view(np.uint32) & 0xffff):
        raise ValueError("attention HE input differs from BF16 residual")
    output_dir.mkdir(parents=True, exist_ok=True)
    x_file = output_dir / "v41_200k_l0_hc_attn_fn_x.f32le.bin"
    y_file = output_dir / "v41_200k_l0_hc_attn_fn_y_raw.f32le.bin"
    x_file.write_bytes(np.ascontiguousarray(x, dtype="<f4").tobytes())
    y_file.write_bytes(np.ascontiguousarray(y, dtype="<f4").tobytes())
    image = json.loads((golden_dir / "images/ctx200000_L00_r0/manifest.json").read_text())
    out = {
        "schema": "opentallas.rtl.v41_fullshape_hc_attn_vectors.v1",
        "status": "golden_vectors_only", "context": CONTEXT, "position": CONTEXT - 1,
        "layer": 0, "rank": 0, "operation": "hc_attn_fn",
        "arithmetic": "HDC_V41_ARITH=chunk8; raw matvec_c return before rsqrt/scale",
        "split_argument": V.HC_SPLIT,
        "weight_shape": list(shape),
        "order": "flat residual h[0,0:5120], h[1], h[2], h[3]; y rows 0..23",
        "dtype": "IEEE-754 binary32 little-endian; x values have BF16 low 16 bits zero",
        "x": {"file": str(x_file.relative_to(ROOT)), "elements": int(x.size),
              "bytes": x_file.stat().st_size, "sha256": sha(x_file)},
        "y_raw": {"file": str(y_file.relative_to(ROOT)), "elements": int(y.size),
                  "bytes": y_file.stat().st_size, "sha256": sha(y_file)},
        "weight_image_sha256": image["files"]["w.hc_attn_fn"]["sha256"],
        "golden_shard": {"input_sha256": shard["input_sha256"],
                         "output_sha256": shard["output_sha256"],
                         "trace_sha256": shard["trace_sha256"]},
        "checkpoint_revision": C.HF.name,
        "checkpoint_index_sha256": sha(C.HF / "model.safetensors.index.json"),
        "golden_model_init_sha256": init_pin,
        "golden_source_sha256": C.golden_pin(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                  cwd=ROOT, text=True).strip(),
        "claim_boundary": "Exact golden intermediate vectors only; no RTL result or timing claim.",
    }
    record.write_text(json.dumps(out, indent=2) + "\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--golden-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=C.SEED,
                        help="seed of the golden shard's synthetic state and token history (tools/"
                             "rtl_v41_fullshape_layer_campaign.py --seed; the default reproduces existing records)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/rtl")
    parser.add_argument("--record", type=Path,
                        default=ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_hc_attn_vectors.json")
    args = parser.parse_args()
    result = export(args.golden_dir, args.output_dir, args.record, seed=args.seed)
    print(json.dumps({"status": result["status"], "x": result["x"], "y_raw": result["y_raw"]}))


if __name__ == "__main__":
    main()
