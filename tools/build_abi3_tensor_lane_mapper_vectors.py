#!/usr/bin/env python3
"""Build source-bound vectors for the ABI 3.0 tensor lane mapper.

The vectors qualify coordinate mapping and backpressure control only.  They do
not claim an integrated tensor datapath, a generated model token, or TPOT.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)


SCHEMA = "opentallas.abi3.tensor_lane_mapper_vectors.v1"
LANES = 256
GROUPS = 4
LANES_PER_GROUP = 64
ERR_NONE = 0
ERR_SHAPE = 7

DEFAULT_IR = (
    ROOT / "results/tensor_accelerator/qwen3_full_model_physical/ir/"
    "tensor_kernel_ir.json"
)
DEFAULT_CAPABILITY = ROOT / "configs/hardware/abi3_capability/hbm_sram_single_chip.json"
DEFAULT_ADR = ROOT / "docs/ABI3_TENSOR_DATAPATH_DECODE_UTILIZATION_ADR.md"
DEFAULT_RTL = ROOT / "rtl/abi3/ot_a3_tensor_lane_mapper.sv"
DEFAULT_OUTPUT = ROOT / "testdata/rtl/abi3_tensor_lane_mapper_vectors.json"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _body_id(value: dict[str, Any], field: str) -> str:
    return _sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )


def _source(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    try:
        name = str(resolved.relative_to(ROOT))
    except ValueError:
        name = str(resolved)
    return {"path": name, "sha256": _sha256_file(resolved)}


def reference_waves(
    rows: int,
    cols: int,
    tile_rows: int,
    tile_cols: int,
    issue_window: int,
) -> tuple[list[dict[str, Any]], int]:
    """Return the independent row-major mapping and folded-output count."""

    if min(rows, cols, tile_rows, tile_cols, issue_window) <= 0:
        return [], 0
    if max(rows, cols, tile_rows, tile_cols, issue_window) > 0xFFFF_FFFF:
        raise ValueError("configuration fields must fit u32")

    waves: list[dict[str, Any]] = []
    seen: set[int] = set()
    folded_outputs = 0
    row_tile_base = 0
    while row_tile_base < rows:
        row_tile_extent = min(tile_rows, rows - row_tile_base)
        row_offset = 0
        while row_offset < row_tile_extent:
            wave_rows = min(row_tile_extent - row_offset, LANES)
            column_capacity = LANES // wave_rows
            if column_capacity < 1:
                raise AssertionError("a nonempty row wave must admit one column")
            column_group_base = 0
            while column_group_base < cols:
                group_end = min(cols, column_group_base + tile_cols * issue_window)
                column_cursor = column_group_base
                while column_cursor < group_end:
                    wave_cols = min(group_end - column_cursor, column_capacity)
                    active = wave_rows * wave_cols
                    if not 1 <= active <= LANES:
                        raise AssertionError("reference emitted an invalid lane count")
                    mask = (1 << active) - 1
                    group_counts = [
                        min(
                            LANES_PER_GROUP,
                            max(0, active - group * LANES_PER_GROUP),
                        )
                        for group in range(GROUPS)
                    ]
                    for local_row in range(wave_rows):
                        for local_col in range(wave_cols):
                            row = row_tile_base + row_offset + local_row
                            col = column_cursor + local_col
                            linear = row * cols + col
                            if linear in seen:
                                raise AssertionError(
                                    f"duplicate logical coordinate ({row}, {col})"
                                )
                            seen.add(linear)
                    waves.append(
                        {
                            "active_lanes": active,
                            "col_base": column_cursor,
                            "cols_per_row": wave_cols,
                            "group_active_counts": group_counts,
                            "lane_valid_hex": f"{mask:064x}",
                            "last": False,
                            "row_base": row_tile_base + row_offset,
                            "rows": wave_rows,
                        }
                    )
                    folded_outputs += active - wave_rows
                    column_cursor += wave_cols
                column_group_base = group_end
            row_offset += wave_rows
        row_tile_base += row_tile_extent

    if len(seen) != rows * cols:
        raise AssertionError(
            f"mapping covered {len(seen)} of {rows * cols} logical outputs"
        )
    if waves:
        waves[-1]["last"] = True
    return waves, folded_outputs


def _case(
    name: str,
    case_class: str,
    *,
    rows: int,
    cols: int,
    tile_rows: int,
    tile_cols: int,
    issue_window: int,
    source_shape: str | None = None,
) -> dict[str, Any]:
    valid = min(rows, cols, tile_rows, tile_cols, issue_window) > 0
    waves, folded = reference_waves(rows, cols, tile_rows, tile_cols, issue_window)
    logical_outputs = rows * cols if valid else 0
    result: dict[str, Any] = {
        "class": case_class,
        "config": {
            "cols": cols,
            "issue_window": issue_window,
            "rows": rows,
            "tile_cols": tile_cols,
            "tile_rows": tile_rows,
        },
        "expected": {
            "active_lane_slots": logical_outputs,
            "error_code": ERR_NONE if valid else ERR_SHAPE,
            "logical_output_count": logical_outputs,
            "masked_lane_slots": len(waves) * LANES - logical_outputs,
            "row_folded_output_count": folded,
            "wave_count": len(waves),
            "waves": waves,
        },
        "name": name,
    }
    if source_shape is not None:
        result["source_shape"] = source_shape
    return result


def _qwen_shape_assertions(ir: dict[str, Any]) -> dict[str, int]:
    kernels = ir.get("kernels")
    if not isinstance(kernels, list):
        raise ValueError("Qwen Kernel IR has no kernel list")
    hidden_matmuls = [
        item
        for item in kernels
        if item.get("kind") == "MATMUL"
        and item.get("shape", {}).get("width") == 4096
        and isinstance(item.get("shape", {}).get("rows"), dict)
        and item["shape"]["rows"].get("maximum") == 8000
    ]
    vocabulary_heads = [
        item
        for item in kernels
        if item.get("kind") == "MATMUL"
        and item.get("shape", {}).get("rows") == 1
        and item.get("shape", {}).get("width") == 151936
    ]
    intermediate_matmuls = [
        item
        for item in kernels
        if item.get("kind") == "MATMUL" and item.get("shape", {}).get("width") == 12288
    ]
    if not hidden_matmuls or not vocabulary_heads or not intermediate_matmuls:
        raise ValueError("Qwen IR no longer contains the admitted real shapes")
    return {
        "context_tokens": 8000,
        "hidden_width": 4096,
        "intermediate_width": 12288,
        "vocabulary_width": 151936,
    }


def build(
    *,
    kernel_ir_path: Path = DEFAULT_IR,
    capability_path: Path = DEFAULT_CAPABILITY,
    adr_path: Path = DEFAULT_ADR,
    rtl_path: Path = DEFAULT_RTL,
) -> dict[str, Any]:
    ir = load_strict_json(kernel_ir_path)
    capability = load_strict_json(capability_path)
    real_shapes = _qwen_shape_assertions(ir)
    tensor = capability.get("engines", {}).get("tensor", {})
    if tensor.get("lanes") != LANES or tensor.get("queues") != GROUPS:
        raise ValueError("capability no longer admits four groups and 256 lanes")

    cases: list[dict[str, Any]] = []
    for field in ("rows", "cols", "tile_rows", "tile_cols", "issue_window"):
        config = {
            "rows": 3,
            "cols": 17,
            "tile_rows": 3,
            "tile_cols": 17,
            "issue_window": 1,
        }
        config[field] = 0
        cases.append(_case(f"zero_{field}", "fail_closed_zero_field", **config))

    boundaries = (1, 2, 63, 64, 65, 127, 128, 129, 255, 256, 257)
    for value in boundaries:
        cases.append(
            _case(
                f"row_boundary_{value}",
                "row_boundary",
                rows=value,
                cols=17,
                tile_rows=value,
                tile_cols=17,
                issue_window=1,
            )
        )
        cases.append(
            _case(
                f"column_boundary_{value}",
                "column_boundary",
                rows=3,
                cols=value,
                tile_rows=64,
                tile_cols=64,
                issue_window=4,
            )
        )

    cases.extend(
        [
            _case(
                "qwen_decode_hidden",
                "source_bound_real_shape",
                rows=1,
                cols=real_shapes["hidden_width"],
                tile_rows=64,
                tile_cols=64,
                issue_window=4,
                source_shape="Qwen decode MATMUL [1,4096]",
            ),
            _case(
                "qwen_prefill_tile_hidden",
                "source_bound_real_shape",
                rows=64,
                cols=real_shapes["hidden_width"],
                tile_rows=64,
                tile_cols=64,
                issue_window=4,
                source_shape="Qwen prefill MATMUL active tile [64,4096]",
            ),
            _case(
                "qwen_batch8_decode_hidden",
                "source_bound_real_shape",
                rows=8,
                cols=real_shapes["hidden_width"],
                tile_rows=64,
                tile_cols=64,
                issue_window=4,
                source_shape="Qwen batch-eight decode MATMUL [8,4096]",
            ),
            _case(
                "qwen_decode_intermediate",
                "source_bound_real_shape",
                rows=1,
                cols=real_shapes["intermediate_width"],
                tile_rows=64,
                tile_cols=64,
                issue_window=4,
                source_shape="Qwen decode MATMUL [1,12288]",
            ),
            _case(
                "qwen_vocabulary_head",
                "source_bound_real_shape",
                rows=1,
                cols=real_shapes["vocabulary_width"],
                tile_rows=64,
                tile_cols=64,
                issue_window=4,
                source_shape="Qwen vocabulary projection [1,151936]",
            ),
            _case(
                "qwen_exact_8k_row_extent",
                "source_bound_context_extent",
                rows=real_shapes["context_tokens"],
                cols=1,
                tile_rows=64,
                tile_cols=64,
                issue_window=4,
                source_shape="Qwen exact 8000-token maximum row extent",
            ),
            _case(
                "u32_schedule_product_no_wrap",
                "overflow_boundary",
                rows=1,
                cols=257,
                tile_rows=0xFFFF_FFFF,
                tile_cols=0xFFFF_FFFF,
                issue_window=0xFFFF_FFFF,
            ),
        ]
    )

    wave_count = sum(case["expected"]["wave_count"] for case in cases)
    logical_outputs = sum(case["expected"]["logical_output_count"] for case in cases)
    value: dict[str, Any] = {
        "claim_boundary": {
            "complete_model_token_generated": False,
            "integrated_tensor_datapath": False,
            "standalone_lane_control_rtl": True,
            "target_tpot": False,
        },
        "coverage": {
            "backpressure_required": True,
            "case_count": len(cases),
            "invalid_case_count": sum(
                case["expected"]["error_code"] != ERR_NONE for case in cases
            ),
            "logical_output_count": logical_outputs,
            "source_bound_real_shape_count": sum(
                case["class"].startswith("source_bound") for case in cases
            ),
            "wave_count": wave_count,
        },
        "hardware": {
            "issue_groups": GROUPS,
            "lanes": LANES,
            "lanes_per_group": LANES_PER_GROUP,
        },
        "cases": cases,
        "schema": SCHEMA,
        "sources": {
            "architecture_decision": _source(adr_path),
            "capability": _source(capability_path),
            "kernel_ir": _source(kernel_ir_path),
            "rtl": _source(rtl_path),
            "vector_builder": _source(Path(__file__)),
        },
        "vector_set_id": "",
    }
    value["vector_set_id"] = _body_id(value, "vector_set_id")
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--kernel-ir", type=Path, default=DEFAULT_IR)
    result.add_argument("--capability", type=Path, default=DEFAULT_CAPABILITY)
    result.add_argument("--adr", type=Path, default=DEFAULT_ADR)
    result.add_argument("--rtl", type=Path, default=DEFAULT_RTL)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return result


def main() -> int:
    args = parser().parse_args()
    value = build(
        kernel_ir_path=args.kernel_ir,
        capability_path=args.capability,
        adr_path=args.adr,
        rtl_path=args.rtl,
    )
    write_canonical_json(args.output, value)
    print(
        f"wrote {args.output}: cases={value['coverage']['case_count']} "
        f"waves={value['coverage']['wave_count']} "
        f"logical_outputs={value['coverage']['logical_output_count']} "
        f"id={value['vector_set_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
