#!/usr/bin/env python3
"""Check a per-expert row-split MoE stream on a released V4.1 layer input.

This is a numerical gate for a future nonblocking collective schedule, not a
throughput measurement.  Each rank first quantizes its own 576-value expert
activation.  The seven rank fragments are joined one expert at a time, and
the local output rows are accumulated in the golden's expert-id order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")

import numpy as np

import hdc_golden_v41 as V
from hdc_golden import F, add, bits, mul, to_bf16
from rtl_v41_fullshape_layer_campaign import Checkpoint, build_model, CONFIG, HF


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_w2(w: V.Q8, codes: np.ndarray, exponents: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """Use the golden 32-element block and chunk-8 order on selected output rows."""
    blocks = []
    for b in range(w.shape[1] // 32):
        sl = slice(32 * b, 32 * (b + 1))
        dot = (w.q[rows, sl] @ codes[sl]).astype(F)
        blocks.append(np.ldexp(dot, w.e[rows, b] + exponents[b]).astype(F))
    return to_bf16(V.csum(np.stack(blocks, axis=-1)))


def verify(shard: Path, rows_per_rank: int = 8, fixture: Path | None = None) -> dict:
    with np.load(shard) as z:
        x = np.asarray(z["L0.ffn_norm"], dtype=F)
        shard_ffn = np.asarray(z["L0.ffn"], dtype=F)
    ck = Checkpoint()
    m, _ = build_model(ck)
    L = 0
    score = V.sqrt(V.softplus(V.mv(m.lw(L, "ffn.gate.weight"), x)))
    chosen = V.topk_lowest_index(add(score, m.lw(L, "ffn.gate.bias")), m.k_exp)
    ids = sorted(map(int, chosen))
    den = add(V.seqsum([score[i] for i in ids]), F(1e-20))
    # Include the row boundary and a few interior values on every rank.
    base = np.linspace(0, 1279, rows_per_rank, dtype=np.int64)
    rows = np.concatenate([1280 * rank + base for rank in range(4)])
    streamed = np.zeros(len(rows), dtype=F)
    gathered_code_mismatches = 0
    gathered_exp_mismatches = 0
    expert_output_mismatches = 0
    all_ids = ids + ["shared"]
    fixture_codes, fixture_scales = [], []
    codebook = {int(b): i for i, b in enumerate(V.E4M3.view(np.uint64))}
    for expert in all_ids:
        prefix = (f"{m.P(L)}ffn.experts.{expert}." if expert != "shared"
                  else f"{m.P(L)}ffn.shared_experts.")
        g = V.linear_q(m.w[prefix + "w1.weight"], x)
        u = V.linear_q(m.w[prefix + "w3.weight"], x)
        u = np.clip(u, -m.limit, m.limit).astype(F)
        g = np.minimum(g, m.limit).astype(F)
        a = mul(V.silu(g), u)
        if expert != "shared":
            a = mul(mul(V.div(score[expert], den), m.route_scale), a)
        a = to_bf16(a)
        q, e = V.quant_fp8(a)
        # Four physical rank fragments; concatenate them in original K order.
        fq = [V.quant_fp8(a[r * 576:(r + 1) * 576])[0] for r in range(4)]
        fe = [V.quant_fp8(a[r * 576:(r + 1) * 576])[1] for r in range(4)]
        q_join, e_join = np.concatenate(fq), np.concatenate(fe)
        fixture_codes.append(np.array([codebook[int(b)] for b in q_join.view(np.uint64)], dtype=np.uint8)
                             .reshape(4, 576))
        fixture_scales.append((e_join + 127).astype(np.uint8).reshape(4, 18))
        gathered_code_mismatches += int(np.count_nonzero(q_join != q))
        gathered_exp_mismatches += int(np.count_nonzero(e_join != e))
        w2 = m.w[prefix + "w2.weight"]
        got = _local_w2(w2, q_join, e_join, rows)
        # Independent golden path, same real weights and selected output rows.
        ref = V.linear_q(V.Q8(w2.q[rows], w2.e[rows]), a)
        expert_output_mismatches += int(np.count_nonzero(bits(got) != bits(ref)))
        streamed = add(streamed, got)
    final = to_bf16(streamed)
    # Reference follows the golden's ID-sorted sequential expert accumulation.
    ref_full = m.moe(L, x, None)
    final_mismatches = int(np.count_nonzero(bits(final) != bits(ref_full[rows])))
    shard_mismatches = int(np.count_nonzero(bits(ref_full) != bits(shard_ffn)))
    fixture_sha = None
    if fixture is not None:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(fixture, expert_ids=np.asarray(ids, dtype=np.int16),
                            codes=np.stack(fixture_codes), scales=np.stack(fixture_scales),
                            y_bf16=(bits(ref_full).reshape(4, 1280) >> 16).astype(np.uint16))
        fixture_sha = _sha(fixture)
    return dict(schema="v41_w2_stream_exact_v1", scope="real released L0/200K input, sampled rows; numerical only",
                checkpoint_snapshot=HF.name, checkpoint_index_sha256=_sha(HF / "model.safetensors.index.json"),
                shard_sha256=_sha(shard), source_sha256={
                    "tools/hdc_golden_v41.py": _sha(Path(V.__file__)),
                    "tools/rtl_v41_fullshape_layer_campaign.py": _sha(Path(__file__).with_name("rtl_v41_fullshape_layer_campaign.py")),
                    "tools/v41_w2_stream_exact.py": _sha(Path(__file__)),
                }, expert_ids=ids, rows_checked=len(rows),
                gathered_code_mismatches=gathered_code_mismatches,
                gathered_exp_mismatches=gathered_exp_mismatches,
                expert_output_mismatches=expert_output_mismatches,
                final_mismatches=final_mismatches,
                shard_mismatches=shard_mismatches,
                fixture_path=(str(fixture.resolve().relative_to(Path(__file__).resolve().parents[1]))
                              if fixture else None),
                fixture_sha256=fixture_sha,
                output_bits_sha256=hashlib.sha256(bits(final).tobytes()).hexdigest())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--rows-per-rank", type=int, default=8)
    ap.add_argument("--fixture", type=Path)
    args = ap.parse_args()
    rec = verify(args.shard, args.rows_per_rank, args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: rec[k] for k in ("expert_ids", "rows_checked", "gathered_code_mismatches",
          "gathered_exp_mismatches", "expert_output_mismatches", "final_mismatches",
          "shard_mismatches")}, sort_keys=True))
    if any(rec[k] for k in ("gathered_code_mismatches", "gathered_exp_mismatches",
                             "expert_output_mismatches", "final_mismatches", "shard_mismatches")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
