#!/usr/bin/env python3
"""Source-pinned numerical probe for the shipped Qwen O4 INT8 TP-2 contract.

The o/down projections split their input columns across two dies.  Their
single BF16 scale belongs to the complete output row, so the scaled output is
fl32(fl32(raw_die0 + raw_die1) * scale).  Applying the scale separately on
each die changes the specified FP32 result.  The real-row probe uses an INT8
embedding as a reproducible input vector; it is not an attention activation or
a full-token exactness claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open

import hdc_golden as G
import qwen3_deployment_quality as Q


ROOT = Path(__file__).resolve().parents[1]
TOKENS = (1073, 0, 1, 1000, 4096, 12345, 151000)


def source_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scaled_tp2(codes: np.ndarray, x: np.ndarray, scales: np.ndarray,
               split: int) -> tuple[np.ndarray, np.ndarray]:
    """Return scale-after-fold and scale-before-fold outputs for a K/2 split."""
    assert codes.shape[1] == x.size and x.size % 2 == 0
    khalf = x.size // 2
    p0 = G.matvec(codes[:, :khalf], x[:khalf], split)
    p1 = G.matvec(codes[:, khalf:], x[khalf:], split)
    return (G.mul(G.add(p0, p1), scales),
            G.add(G.mul(p0, scales), G.mul(p1, scales)))


def evaluate(snapshot: Path, rows: int = 128) -> dict:
    config = json.loads((snapshot / "config.json").read_text())
    assert config["hidden_size"] == 4096 and config["vocab_size"] == 151936
    tensor_file = snapshot / "model-00001-of-00005.safetensors"
    with safe_open(str(tensor_file), framework="pt", device="cpu") as h:
        o_weight = h.get_slice("model.layers.0.self_attn.o_proj.weight")[:rows]
        q_weight = h.get_slice("model.layers.0.self_attn.q_proj.weight")[:rows]
        norm = h.get_tensor("model.layers.0.input_layernorm.weight")
        embeddings = h.get_slice("model.embed_tokens.weight")
        token_rows = torch.stack([embeddings[t] for t in TOKENS])

    o_code, o_scale, _ = Q.quantize_w8(o_weight)
    q_folded = (q_weight.float() * norm.float()[None, :]).to(torch.bfloat16)
    q_code, q_scale, _ = Q.quantize_w8(q_folded)
    emb_code, emb_scale, _ = Q.quantize_w8(token_rows)
    oc = o_code.numpy().astype(np.float32)
    os = o_scale.float().numpy().reshape(-1)
    qc = q_code.numpy().astype(np.float32)
    qs = q_scale.float().numpy().reshape(-1)

    # The quality harness uses fused qkv with N=6144 on 8192 groups and the
    # TP-2 emitter uses half its output rows on 6144 groups.  The o projection
    # has all output rows on each die but half its K input on each die.
    q_global_split = G.split_for(6144, 4096, 8192)
    q_die_split = G.split_for(3072, 4096, 6144)
    o_global_split = G.split_for(4096, 4096, 8192)
    o_die_split = G.split_for(4096, 2048, 6144)
    probes = []
    for i, token in enumerate(TOKENS):
        x = G.mul(emb_code[i].float().numpy(), emb_scale[i].float().numpy())
        q_global = G.mul(G.matvec(qc, x, q_global_split), qs)
        q_tp = G.mul(G.matvec(qc, x, q_die_split), qs)
        o_global = G.mul(G.matvec(oc, x, o_global_split), os)
        o_tp, o_wrong = scaled_tp2(oc, x, os, o_die_split)
        q_mismatch = np.flatnonzero(G.bits(q_global) != G.bits(q_tp))
        o_mismatch = np.flatnonzero(G.bits(o_global) != G.bits(o_tp))
        scale_mismatch = np.flatnonzero(G.bits(o_tp) != G.bits(o_wrong))
        first = int(scale_mismatch[0]) if scale_mismatch.size else None
        probes.append({
            "token": token,
            "q_global_vs_tp2_mismatches": int(q_mismatch.size),
            "o_global_vs_tp2_fold_then_scale_mismatches": int(o_mismatch.size),
            "o_fold_then_scale_vs_scale_then_fold_mismatches": int(scale_mismatch.size),
            "first_scale_order_mismatch_row": first,
            "first_correct_bits": int(G.bits(o_tp)[first]) if first is not None else None,
            "first_wrong_bits": int(G.bits(o_wrong)[first]) if first is not None else None,
        })
    sources = (Path(__file__), ROOT / "tools/hdc_golden.py",
               ROOT / "tools/qwen3_deployment_quality.py")
    return {
        "snapshot_revision": snapshot.name,
        "checkpoint_shard_blob": tensor_file.resolve().name,
        "source_sha256": {str(p.relative_to(ROOT)): source_sha(p) for p in sources},
        "rows_per_matrix": rows,
        "quantization": "signed INT8 complete output row, one BF16 scale, norm fold before q quantization",
        "splits": {"q_quality": q_global_split, "q_tp2": q_die_split,
                   "o_quality": o_global_split, "o_tp2_per_die": o_die_split},
        "probes": probes,
        "required_tp2_order": "raw FP32 partials, rank-ordered FP32 fold, one FP32 RNE row-scale multiply",
        "claim_boundary": "Layer-0 real-row numerical probe; embedding input to o is synthetic and no full token, RTL, or throughput is validated.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--snapshot", type=Path, default=Q.find_snapshot())
    parser.add_argument("--rows", type=int, default=128)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = evaluate(args.snapshot, args.rows)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload)
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
