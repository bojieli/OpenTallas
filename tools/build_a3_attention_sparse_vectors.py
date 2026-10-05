#!/usr/bin/env python3
"""End-to-end vectors for ot_a3_attention_sparse from the reference's own API.

``sparse_attention_bf16_codes`` is the public entry point of
runtime/tensor_accelerator/sparse_attention.py, and this generator calls it.
Nothing here reimplements any part of the operator: the inputs are random BF16
encodings and the expectations are whatever the reference returns -- output
codes, the final maxima, the sink exponentials, the denominators and the
saturation count.

That makes this the only test in the ATTENTION.SPARSE set that can catch a
COMPOSITION error. Each part was qualified against the reference on its own, so
a wrong block order, a running maximum carried across a row boundary, a rescale
applied to the wrong block or a probability narrowed twice would leave every
component test green and show up only here.

Shapes are small because the cost is real: one shipped head is 64 lanes x 512
channels x two walks per source block, and the shipped descriptor has 64 heads
and 133 candidates. The frozen 64-slot block is NOT scaled down -- it is part of
the numeric contract -- so a 6-candidate case still walks 64 lanes and exercises
the padded tail, which is the point.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.tensor_accelerator.sparse_attention import (  # noqa: E402
    sparse_attention_bf16_codes,
)

#: The shipped descriptors' own score scale, 1/sqrt(512) in binary32.
SHIPPED_SCALE = 0x3D3504F3

QUERY_BASE = 0
INDEX_BASE = 2048
SINK_BASE = 3072
KV_BASE = 4096
OUT_BASE = 16384


def bf16(values: np.ndarray) -> np.ndarray:
    bits = np.ascontiguousarray(values.astype(np.float32)).view(np.uint32)
    lower = bits & np.uint32(0xFFFF)
    rounded = bits >> np.uint32(16)
    up = (lower > np.uint32(0x8000)) | (
        (lower == np.uint32(0x8000)) & ((rounded & np.uint32(1)) == np.uint32(1))
    )
    return (rounded + up.astype(np.uint32)).astype(np.uint16)


#: name, span, heads, head_dim, slots, kv_rows, index kind
#:
#: head_dim IS 16 OR MORE, which is the smallest any shipped ATTENTION.SPARSE
#: uses. It is not a free choice: the AV walk's inner pass is head_dim long and
#: carries the accumulator hazard, so it refuses a head_dim at or below its
#: product-add pipeline depth -- MAC_LAT + 2, which is 8 with the split rounding
#: stage. An earlier revision of this suite used 8, and moving the product-add to
#: six stages turned every case into a shape refusal.
CASES = [
    ("one_block", 1, 2, 16, 6, 8, "random"),
    ("full_block", 1, 2, 16, 64, 32, "random"),
    #: Two source blocks: the online rescale has to actually do something.
    ("two_blocks", 1, 2, 16, 70, 96, "random"),
    ("three_blocks", 1, 1, 16, 133, 160, "random"),
    #: Several query rows through one instance: the running maximum and the
    #: denominator must not survive a row boundary.
    ("multi_row", 3, 2, 16, 6, 8, "random"),
    #: Several rows AND several blocks. With one block per row a sequencer that
    #: forgets to rewind the block cursor at a row boundary is invisible, which a
    #: mutation of exactly that showed: the single-block multi-row case above
    #: passed with the rewind deleted.
    ("multi_row_blocks", 2, 2, 16, 70, 96, "random"),
    ("wide_head", 1, 1, 32, 64, 64, "random"),
    #: "duplicate_index_policy": "preserve_every_source_slot"
    ("duplicates", 1, 2, 16, 12, 8, "duplicate"),
    #: One valid slot in the first block is the contract's minimum.
    ("single_valid", 1, 2, 16, 1, 8, "random"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES))]
    for index, (name, span, heads, head_dim, slots, kv_rows, kind) in enumerate(CASES):
        rng = np.random.default_rng(0x5A5A + index)
        queries = bf16(rng.standard_normal((span, heads, head_dim)) * 0.7)
        kv = bf16(rng.standard_normal((kv_rows, head_dim)) * 0.7)
        sink = np.ascontiguousarray(
            (rng.standard_normal(heads) * 0.5).astype(np.float32)
        ).view(np.uint32)
        if kind == "duplicate":
            base = rng.integers(0, kv_rows, size=(span, 2)).astype(np.int64)
            indices = np.repeat(base, slots // 2, axis=1)[:, :slots]
        else:
            indices = rng.integers(0, kv_rows, size=(span, slots)).astype(np.int64)

        result = sparse_attention_bf16_codes(
            queries, kv, sink, indices, scale_binary32=SHIPPED_SCALE
        )

        def dump(tag: str, words: np.ndarray) -> None:
            (args.out / f"{tag}_{index}.hex").write_text(
                "\n".join(f"{int(w):08x}" for w in words.reshape(-1)) + "\n")

        dump("q", queries.astype(np.uint32))
        dump("kv", kv.astype(np.uint32))
        dump("sink", sink.astype(np.uint32))
        #: -1 padding reaches the device as a 32-bit two's complement word.
        dump("idx", (indices.astype(np.int64) & 0xFFFFFFFF).astype(np.uint64))
        dump("out", result.values.astype(np.uint32))

        lines.append(
            f"{name} {span} {heads} {head_dim} {slots} {kv_rows} "
            f"{int(result.output_saturated_element_count)}"
        )
        live = int((indices >= 0).sum())
        print(f"  {name:<14} span={span} heads={heads} head_dim={head_dim} "
              f"slots={slots} live={live} "
              f"blocks={(slots + 63) // 64} oracle_rows={result.oracle_rows}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(CASES)} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
