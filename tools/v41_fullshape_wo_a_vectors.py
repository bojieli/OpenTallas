#!/usr/bin/env python3
"""Export checkpoint-backed V4.1 L0 rank-0 grouped wo_a exact gate vectors.

The wrapper observes Model.attend's existing matvec_c call. It calls the
original arithmetic unchanged and checks the resulting full layer against the
source-pinned golden shard before writing any vector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

import rtl_v41_fullshape_layer_campaign as C
V = C.V  # campaign sets HDC_V41_ARITH=chunk8 before importing the golden

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = 200000
LAYER = 0
RANK = 0


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def export(golden_dir: Path, output_dir: Path, record: Path) -> dict:
    shard = json.loads((golden_dir / "ctx200000_L00.json").read_text())
    if shard["arith"] != "chunk8" or shard["context"] != CONTEXT or shard["layer"] != LAYER:
        raise ValueError("wrong golden shard/arithmetic")
    ck = C.Checkpoint()
    m, init_pin = C.build_model(ck, engram=False)
    st, state_desc = C.synthetic_state(m, CONTEXT, layers=[LAYER])
    hist = C.token_history(CONTEXT)
    tok = hist[-1]
    h = np.repeat(ck.rows("embed.weight", [tok]), m.hc, axis=0).astype(np.float32)
    pre = np.array([1, 0, 0, 0], dtype=np.float32)[:m.hc]
    if C.digest(h, pre) != shard["input_sha256"]:
        raise ValueError("rerun input differs from pinned golden shard")
    context = {"pos": CONTEXT - 1, "hist": hist, "h": h, "pre": pre}
    captured: list[tuple[np.ndarray, np.ndarray]] = []
    original = V.matvec_c
    group_k = m.heads * m.hd // m.groups

    def observe(w, x, split, cls="me"):
        result = original(w, x, split, cls)
        if (np.shape(w) == (m.o_rank, group_k) and np.shape(x) == (group_k,)
                and split == V.WO_A_SPLIT and cls == "me"):
            captured.append((np.asarray(x, dtype=np.float32).copy(),
                             np.asarray(result, dtype=np.float32).copy()))
        return result

    V.matvec_c = observe
    try:
        m.layer(LAYER, context, st, {})
    finally:
        V.matvec_c = original
    if C.digest(context["h"], context["pre"]) != shard["output_sha256"]:
        raise ValueError("rerun layer output differs from pinned golden shard")
    if len(captured) != m.groups or m.groups % 4:
        raise ValueError(f"captured {len(captured)} wo_a groups, expected {m.groups}")
    # TP4 output-group split: rank 0 owns the first two of eight groups.
    per_rank = m.groups // 4
    acc = np.ascontiguousarray(np.concatenate([x for x, _ in captured[:per_rank]]), dtype="<f4")
    za = np.ascontiguousarray(np.concatenate([y for _, y in captured[:per_rank]]), dtype="<f4")
    if acc.size != 8192 or za.size != 2048 or np.any(acc.view(np.uint32) & 0xffff):
        raise ValueError("rank-0 wo_a vector shape or BF16 ACC contract mismatch")
    output_dir.mkdir(parents=True, exist_ok=True)
    acc_file = output_dir / "v41_200k_l0_wo_a_acc_rank0.f32le.bin"
    za_file = output_dir / "v41_200k_l0_wo_a_za_rank0.f32le.bin"
    acc_file.write_bytes(acc.tobytes())
    za_file.write_bytes(za.tobytes())
    image = json.loads((golden_dir / "images/ctx200000_L00_r0/manifest.json").read_text())
    out = {
        "schema": "opentallas.rtl.v41_fullshape_wo_a_vectors.v1", "status": "golden_vectors_only",
        "context": CONTEXT, "position": CONTEXT - 1, "layer": LAYER, "rank": RANK,
        "arithmetic": "HDC_V41_ARITH=chunk8, original matvec_c return before to_bf16",
        "wo_a_split_argument": V.WO_A_SPLIT,
        "tp": 4, "total_groups": m.groups, "rank_groups": [0, per_rank - 1],
        "group_input_elements": group_k, "group_output_elements": m.o_rank,
        "order": "flat group-major: group 0 elements in increasing index, then group 1",
        "dtype": "IEEE-754 binary32 little-endian; ACC values have BF16 low 16 bits zero",
        "acc": {"file": str(acc_file.relative_to(ROOT)), "elements": int(acc.size),
                "bytes": acc_file.stat().st_size, "sha256": sha(acc_file.read_bytes())},
        "za": {"file": str(za_file.relative_to(ROOT)), "elements": int(za.size),
               "bytes": za_file.stat().st_size, "sha256": sha(za_file.read_bytes())},
        "golden_shard": {"input_sha256": shard["input_sha256"],
                         "output_sha256": shard["output_sha256"],
                         "trace_sha256": shard["trace_sha256"]},
        "weight_image_wo_a_sha256": image["files"]["w.wo_a"]["sha256"],
        "checkpoint_revision": C.HF.name,
        "checkpoint_index_sha256": sha((C.HF / "model.safetensors.index.json").read_bytes()),
        "golden_model_init_sha256": init_pin,
        "golden_source_sha256": C.golden_pin(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                  cwd=ROOT, text=True).strip(),
        "claim_boundary": "Exact golden intermediate vectors only; no RTL result or timing claim.",
    }
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(out, indent=2) + "\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--golden-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/rtl")
    parser.add_argument("--record", type=Path,
                        default=ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_wo_a_vectors.json")
    args = parser.parse_args()
    result = export(args.golden_dir, args.output_dir, args.record)
    print(json.dumps({"status": result["status"], "acc": result["acc"], "za": result["za"]}))


if __name__ == "__main__":
    main()
