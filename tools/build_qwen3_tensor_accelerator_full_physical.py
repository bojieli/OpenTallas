#!/usr/bin/env python3
"""Build and independently reconstruct the complete Qwen HBM/SRAM image."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.qwen_full_model_physical import (  # noqa: E402
    QwenFullModelPhysicalError,
    build_qwen_full_model_physical_deployment,
)
from compiler.tensor_accelerator.qwen_full_model_physical_checking import (  # noqa: E402
    QwenFullModelPhysicalCheckError,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile all 617 Qwen3-8B graph operations and 399 locked weights "
            "into one sharded HBM image plus a live-range-checked SRAM/ABI 2.5 "
            "program. The command performs independent physical reconstruction "
            "but does not execute the model."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--checkpoint-lock", required=True, type=Path)
    parser.add_argument(
        "--model-graph",
        type=Path,
        default=ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json",
    )
    parser.add_argument(
        "--capability",
        type=Path,
        default=ROOT / "configs/hardware/tensor_accelerator_development_v6.json",
    )
    parser.add_argument(
        "--semantic-coverage",
        type=Path,
        default=(
            ROOT / "results/tensor_accelerator/qwen3_full_model_semantics/coverage.json"
        ),
    )
    parser.add_argument(
        "--semantic-kernel-ir",
        type=Path,
        default=(
            ROOT / "results/tensor_accelerator/qwen3_full_model_semantics/"
            "tensor_kernel_ir.json"
        ),
    )
    parser.add_argument(
        "--semantic-check",
        type=Path,
        default=(
            ROOT / "results/tensor_accelerator/qwen3_full_model_semantics/"
            "independent_check.json"
        ),
    )
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        manifest = build_qwen_full_model_physical_deployment(
            snapshot=arguments.snapshot,
            checkpoint_lock_path=arguments.checkpoint_lock,
            model_graph_path=arguments.model_graph,
            capability_path=arguments.capability,
            semantic_coverage_path=arguments.semantic_coverage,
            semantic_kernel_ir_path=arguments.semantic_kernel_ir,
            semantic_check_path=arguments.semantic_check,
            output=arguments.output,
        )
    except (QwenFullModelPhysicalError, QwenFullModelPhysicalCheckError) as exc:
        parser.error(str(exc))
    print(f"build_id={manifest['build_id']}")
    print(f"physical_plan_id={manifest['physical_plan_id']}")
    print(f"independent_check_id={manifest['independent_check_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
