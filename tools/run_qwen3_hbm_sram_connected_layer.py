#!/usr/bin/env python3
"""Build, independently check, and execute one connected Qwen layer."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.production_connected_layer import (  # noqa: E402
    build_connected_layer_deployment,
)
from runtime.tensor_accelerator.production_connected_layer_simulator import (  # noqa: E402
    ProductionConnectedLayerSimulator,
    publish_connected_layer_execution_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile and causally execute one authenticated Qwen3-8B layer-0 "
            "token from embedding lookup through transactional KV attention, "
            "output projection, residuals, MLP, hidden.1, and state commit on "
            "the HBM/SRAM tensor accelerator."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--checkpoint-lock", required=True, type=Path)
    parser.add_argument("--model-graph", required=True, type=Path)
    parser.add_argument("--capability", required=True, type=Path)
    parser.add_argument("--qkv-qualification", required=True, type=Path)
    parser.add_argument("--qkv-execution", required=True, type=Path)
    parser.add_argument("--attention-qualification", required=True, type=Path)
    parser.add_argument("--attention-execution", required=True, type=Path)
    parser.add_argument("--downstream-qualification", required=True, type=Path)
    parser.add_argument("--downstream-execution", required=True, type=Path)
    parser.add_argument("--deployment", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    arguments = parser.parse_args()

    manifest = build_connected_layer_deployment(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        model_graph_path=arguments.model_graph,
        capability_path=arguments.capability,
        qkv_qualification_path=arguments.qkv_qualification,
        qkv_execution_path=arguments.qkv_execution,
        attention_qualification_path=arguments.attention_qualification,
        attention_execution_path=arguments.attention_execution,
        downstream_qualification_path=arguments.downstream_qualification,
        downstream_execution_path=arguments.downstream_execution,
        output=arguments.deployment,
    )
    report = ProductionConnectedLayerSimulator.load(arguments.deployment).execute()
    publish_connected_layer_execution_report(report, arguments.report)
    print(f"build_id={manifest['build_id']}")
    print(f"report_id={report['report_id']}")
    print(f"hidden_1_sha256={report['output']['hidden_1']['payload_sha256']}")
    print(f"state_sha256={report['state']['state_sha256']}")
    print(f"command_count={report['command_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
