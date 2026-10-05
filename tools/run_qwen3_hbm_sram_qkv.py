#!/usr/bin/env python3
"""Build, independently check, and execute real Qwen Q/K/V preparation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.production_qkv import (  # noqa: E402
    build_qkv_deployment,
)
from compiler.tensor_accelerator.qkv_qualification import (  # noqa: E402
    load_qkv_qualification,
)
from runtime.tensor_accelerator.production_qkv_simulator import (  # noqa: E402
    ProductionQKVSimulationError,
    ProductionQKVSimulator,
    publish_qkv_execution_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile and causally execute one authenticated Qwen token through "
            "layer-0 embedding, input normalization, Q/K/V projection, per-head "
            "normalization, and position-indexed RoPE on the HBM/SRAM tensor "
            "accelerator."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--checkpoint-lock", required=True, type=Path)
    parser.add_argument("--model-graph", required=True, type=Path)
    parser.add_argument("--capability", required=True, type=Path)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--deployment", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    arguments = parser.parse_args()

    manifest = build_qkv_deployment(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        model_graph_path=arguments.model_graph,
        capability_path=arguments.capability,
        qualification_path=arguments.qualification,
        output=arguments.deployment,
    )
    qualification = load_qkv_qualification(arguments.qualification)
    report = ProductionQKVSimulator.load(arguments.deployment).execute()
    observed_intermediates = {
        role: record["payload_sha256"]
        for role, record in report["intermediates"].items()
    }
    expected_intermediates = {
        role: record["payload_sha256"]
        for role, record in qualification["intermediates"].items()
    }
    observed_outputs = {
        role: record["payload_sha256"] for role, record in report["outputs"].items()
    }
    expected_outputs = {
        role: record["payload_sha256"]
        for role, record in qualification["outputs"].items()
    }
    if (
        observed_intermediates != expected_intermediates
        or observed_outputs != expected_outputs
    ):
        raise ProductionQKVSimulationError(
            "artifact-only Q/K/V values differ from qualification evidence"
        )
    for role, selected in qualification["selected_reference"]["output"].items():
        output_role = {"q": "q_rotary", "k": "k_rotary", "v": "v"}[role]
        observed = [
            report["outputs"][output_role]["codes"][index]
            for index in selected["element_indices"]
        ]
        if observed != selected["codes"]:
            raise ProductionQKVSimulationError(
                f"artifact-only selected {role.upper()} outputs differ from scalar "
                "reference evidence"
            )
    publish_qkv_execution_report(report, arguments.report)
    print(f"build_id={manifest['build_id']}")
    print(f"report_id={report['report_id']}")
    for role in sorted(observed_outputs):
        print(f"{role}_sha256={observed_outputs[role]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
