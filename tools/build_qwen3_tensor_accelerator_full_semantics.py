#!/usr/bin/env python3
"""Build and independently check complete Qwen neutral semantic artifacts."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import canonical_json_bytes  # noqa: E402
from compiler.tensor_accelerator.qwen_full_model_semantics import (  # noqa: E402
    QwenFullModelSemanticError,
    build_qwen_full_model_semantics,
)
from compiler.tensor_accelerator.qwen_full_model_semantics_checking import (  # noqa: E402
    QwenFullModelSemanticCheckError,
    check_qwen_full_model_semantics,
)


def _write_synced(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(dict(value)))
        handle.flush()
        os.fsync(handle.fileno())


def _publish(arguments: argparse.Namespace) -> tuple[str, str, str]:
    output = Path(arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise QwenFullModelSemanticError(
            f"semantic bundle will not be overwritten: {output}"
        )
    staging = Path(
        tempfile.mkdtemp(dir=output.parent, prefix=f".{output.name}.", suffix=".tmp")
    )
    try:
        coverage, kernel_ir = build_qwen_full_model_semantics(
            model_graph_path=arguments.model_graph,
            capability_path=arguments.capability,
            qkv_qualification_path=arguments.qkv_qualification,
            attention_qualification_path=arguments.attention_qualification,
            layer_qualification_path=arguments.layer_qualification,
            final_output_qualification_path=arguments.final_output_qualification,
        )
        coverage_path = staging / "coverage.json"
        kernel_path = staging / "tensor_kernel_ir.json"
        check_path = staging / "independent_check.json"
        _write_synced(coverage_path, coverage)
        _write_synced(kernel_path, kernel_ir)
        check = check_qwen_full_model_semantics(
            model_graph_path=arguments.model_graph,
            capability_path=arguments.capability,
            coverage_path=coverage_path,
            kernel_ir_path=kernel_path,
            qkv_qualification_path=arguments.qkv_qualification,
            attention_qualification_path=arguments.attention_qualification,
            layer_qualification_path=arguments.layer_qualification,
            final_output_qualification_path=arguments.final_output_qualification,
        )
        _write_synced(check_path, check)
        if output.exists():
            raise QwenFullModelSemanticError(
                f"semantic bundle will not be overwritten: {output}"
            )
        os.rename(staging, output)
        return coverage["report_id"], kernel_ir["kernel_ir_id"], check["check_id"]
    finally:
        if staging.exists():
            for child in staging.iterdir():
                child.unlink()
            staging.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser()
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
        "--qkv-qualification",
        type=Path,
        default=ROOT / "results/tensor_accelerator/qwen3_qkv_qualification.json",
    )
    parser.add_argument(
        "--attention-qualification",
        type=Path,
        default=(
            ROOT / "results/tensor_accelerator/qwen3_attention_qualification.json"
        ),
    )
    parser.add_argument(
        "--layer-qualification",
        type=Path,
        default=ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json",
    )
    parser.add_argument(
        "--final-output-qualification",
        type=Path,
        default=(
            ROOT / "results/tensor_accelerator/qwen3_final_output_qualification.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(ROOT / "results/tensor_accelerator/qwen3_full_model_semantics"),
    )
    arguments = parser.parse_args()
    try:
        report_id, kernel_ir_id, check_id = _publish(arguments)
    except (QwenFullModelSemanticError, QwenFullModelSemanticCheckError) as exc:
        parser.error(str(exc))
    print(f"coverage_report_id={report_id}")
    print(f"kernel_ir_id={kernel_ir_id}")
    print(f"independent_check_id={check_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
