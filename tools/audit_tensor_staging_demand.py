#!/usr/bin/env python3
"""Bound the current G2 weight stream against actual BF16 contraction geometry.

This is capacity/service arithmetic from the IR and the LQ8 stream order, not a
simulation of an integrated accelerator. Non-BF16 contracts are refused rather
than assigned the BF16 group width. Per-row stream repeats are local SRAM reads,
not automatically external memory refetches in an architecture with residency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def demand(rows: int, columns: int, depth: int, lanes: int = 8) -> dict:
    if min(rows, columns, depth, lanes) < 1 or columns % lanes:
        raise ValueError("positive geometry and lane-divisible columns required")
    words_per_row = columns // lanes * depth
    stream_words = rows * words_per_row
    return {
        "rows": rows,
        "columns": columns,
        "depth": depth,
        "lanes": lanes,
        "weight_stream_words": stream_words,
        "weight_stream_read_bytes": stream_words * lanes * 2,
        "unique_weight_bytes": columns * depth * 2,
        "current_window_words": 1024,
        "fits_current_preloaded_weight_window": stream_words <= 1024,
        "minimum_512_word_bank_fills_without_row_reuse": (stream_words + 511) // 512,
        "minimum_512_word_bank_fills_with_perfect_row_reuse": (words_per_row + 511)
        // 512,
        "one_output_group_depth_fits_bank": depth <= 512,
        "one_output_group_depth_fits_whole_window": depth <= 1024,
        "activation_row_bytes": depth * 2,
        "activation_row_fits_2k_window": depth * 2 <= 2048,
    }


def build(ir_path: Path, spans: list[int]) -> dict:
    ir = json.loads(ir_path.read_text())
    contractions = [
        k for k in ir["kernels"] if k["kind"] in ("MATMUL", "VOCAB_PROJECT")
    ]
    cases = []
    for span in spans:
        kernels = []
        for k in contractions:
            attrs = k["attributes"]
            if attrs.get("input_dtype") != "bf16" or not k[
                "numeric_contract"
            ].startswith("bf16_bf16_fp32_"):
                raise ValueError(f"unsupported contraction contract: {k['kernel_id']}")
            domain = k["iteration_domain"]
            tokens = domain["tokens"]
            if isinstance(tokens, dict):
                if (
                    tokens["symbol"] != "span_tokens"
                    or not 0 < span <= tokens["maximum"]
                ):
                    raise ValueError(
                        "unsupported or out-of-range symbolic token extent"
                    )
                rows = span * tokens.get("multiplier", 1)
            else:
                rows = int(tokens)
            kernels.append(
                {
                    "kernel_id": k["kernel_id"],
                    "contract": k["numeric_contract"],
                    **demand(rows, domain["output_width"], domain["reduction_width"]),
                }
            )
        cases.append(
            {
                "span_tokens": span,
                "contractions": kernels,
                "contraction_count": len(kernels),
                "fit_current_window_count": sum(
                    k["fits_current_preloaded_weight_window"] for k in kernels
                ),
                "total_unique_weight_bytes": sum(
                    k["unique_weight_bytes"] for k in kernels
                ),
                "total_weight_stream_read_bytes": sum(
                    k["weight_stream_read_bytes"] for k in kernels
                ),
            }
        )
    sources = [
        ir_path,
        ROOT / "rtl/abi3/ot_a3_lq8.sv",
        ROOT / "rtl/abi3/ot_a3_lane_pipelined.sv",
        ROOT / "rtl/abi3/ot_a3_g2_array_staging.sv",
        ROOT / "rtl/abi3/ot_a3_g2_cluster.sv",
        Path(__file__),
    ]
    return {
        "schema": "opentallas.tensor_staging_demand.v1",
        "model_id": ir["model_id"],
        "scope": "Geometry stress test of direct whole-contraction G2 execution at LANES=8, group=1, zero weight base, no weight reuse across rows. Not the compiler's tiled execution, not measured traffic or a complete activation-address model. Perfection of row reuse is only a lower bound; ports, scales, partial state and ownership must be implemented.",
        "sources": {
            str(p.resolve().relative_to(ROOT)): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sources
        },
        "cases": cases,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir", type=Path, required=True)
    ap.add_argument("--span", nargs="+", type=int, default=[1, 8, 128])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    body = build(args.ir, args.span)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    for c in body["cases"]:
        print(
            f"span={c['span_tokens']}: {c['fit_current_window_count']}/{c['contraction_count']} whole contractions fit; stream reads={c['total_weight_stream_read_bytes']} B, unique weights={c['total_unique_weight_bytes']} B"
        )
