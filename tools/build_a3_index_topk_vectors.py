#!/usr/bin/env python3
"""Vectors for ot_a3_route_index_topk, from the reference's own selection.

``index_topk_indices`` in runtime/reference/selection.py is the authority for
the whole operator -- the causal compressed-position mask, the stable top-k, the
offset, and the -1 a masked selection becomes. ``stable_topk_bf16`` underneath
it fixes the ordering as (rank, value, -index) descending, which is
``TIE_POLICY = score_descending_then_logical_index_ascending``.

Cases cover what a top-k gets wrong: exact ties (which the index has to break),
both infinities, negative and positive zero together (equal in value, so the tie
falls to the index and a monotone bit map that separates them reverses it), the
prefill mask at every query, k clamped by the candidate count, and a nonzero
view offset.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.reference.selection import index_topk_indices  # noqa: E402

NEG_INF = 0xFF80
POS_INF = 0x7F80


def bf16(values: np.ndarray) -> np.ndarray:
    bits = np.ascontiguousarray(values.astype(np.float32)).view(np.uint32)
    lower = bits & np.uint32(0xFFFF)
    rounded = bits >> np.uint32(16)
    up = (lower > np.uint32(0x8000)) | (
        (lower == np.uint32(0x8000)) & ((rounded & np.uint32(1)) == np.uint32(1))
    )
    return (rounded + up.astype(np.uint32)).astype(np.uint16)


#: name, start_position, sequence, ratio, top_k, offset, score kind
CASES = [
    ("decode_small",   63,  1, 4,   8,    0, "random"),
    ("decode_offset",  63,  1, 4,   8, 1000, "random"),
    ("decode_k_clamp", 15,  1, 4,  16,    0, "random"),
    ("prefill_mask",    0, 12, 4,   3,    0, "random"),
    ("prefill_wide",    0, 32, 4,   8,   64, "random"),
    #: Every score identical, so the whole order is the index tie-break.
    ("all_tied",       63,  1, 4,  16,    0, "tied"),
    #: Half the row tied, the rest distinct.
    ("half_tied",      63,  1, 4,  12,    0, "half_tied"),
    #: Both zeros in one row. An infinity is NOT a case here: the reference
    #: validates its scores with finite=True, so a nonfinite score is a refusal
    #: rather than a value to order, and the bench checks that refusal directly.
    ("zeros",          63,  1, 4,  16,    0, "zeros"),
    ("zeros_wide",    255,  1, 4,  32,    7, "zeros"),
]


def row_for(kind: str, n: int, rng: np.random.Generator) -> np.ndarray:
    if kind == "tied":
        return np.full(n, bf16(np.array([0.375]))[0], dtype=np.uint16)
    if kind == "half_tied":
        out = bf16(rng.standard_normal(n))
        out[: n // 2] = bf16(np.array([-0.25]))[0]
        return out
    if kind == "zeros":
        out = bf16(rng.standard_normal(n))
        #: Negative zero and positive zero are EQUAL in value, so the tie falls
        #: to the index -- a monotone map that does not collapse them first
        #: orders 0x8000 above 0x0000 and reverses that.
        out[2] = 0x8000
        out[5] = 0x0000
        out[9] = 0x8000
        out[11] = 0x0000
        return out
    return bf16(rng.standard_normal(n))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    header: list[str] = []
    rows_emitted = 0
    index = 0
    for (name, start, seq, ratio, top_k, offset, kind) in CASES:
        rng = np.random.default_rng(0x707 + len(name))
        candidates = (start + seq) // ratio
        matrix = np.stack([row_for(kind, candidates, rng) for _ in range(seq)])
        result = index_topk_indices(
            [[[int(v) for v in row] for row in matrix]],
            top_k=top_k, compression_ratio=ratio,
            start_position=start, offset=offset,
        )
        selected = min(top_k, candidates)
        for query in range(seq):
            valid = ((query + 1) // ratio) if start == 0 else candidates
            (args.out / f"tk_score_{index}.hex").write_text(
                "\n".join(f"{int(v):08x}" for v in matrix[query]) + "\n")
            expected = result[0][query]
            (args.out / f"tk_out_{index}.hex").write_text(
                "\n".join(f"{(int(v) & 0xFFFFFFFF):08x}" for v in expected) + "\n")
            header.append(
                f"{name}_q{query} {candidates} {top_k} {valid} {offset} {selected}")
            index += 1
            rows_emitted += 1

    (args.out / "cases.txt").write_text(
        "\n".join([str(rows_emitted)] + header) + "\n")
    print(f"wrote {rows_emitted} rows to {args.out}")
    for line in header[:4]:
        print("  ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
