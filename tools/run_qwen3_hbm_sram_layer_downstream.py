#!/usr/bin/env python3
"""Build, independently check, and execute Qwen layer-0 downstream work."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.layer_qualification import (  # noqa: E402
    load_layer_qualification,
)
from compiler.tensor_accelerator.production_layer_downstream import (  # noqa: E402
    build_layer_downstream_deployment,
)
from runtime.tensor_accelerator.production_layer_downstream_simulator import (  # noqa: E402
    ProductionLayerDownstreamSimulationError,
    ProductionLayerDownstreamSimulator,
    publish_layer_downstream_execution_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile and causally execute authenticated Qwen layer-0 attention "
            "output and hidden residual through output projection, residual, "
            "post-attention RMSNorm, MLP, and final residual on the HBM/SRAM "
            "tensor accelerator."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--checkpoint-lock", required=True, type=Path)
    parser.add_argument("--model-graph", required=True, type=Path)
    parser.add_argument("--capability", required=True, type=Path)
    parser.add_argument("--qualification", required=True, type=Path)
    parser.add_argument("--attention-execution", required=True, type=Path)
    parser.add_argument("--deployment", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    arguments = parser.parse_args()

    manifest = build_layer_downstream_deployment(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        model_graph_path=arguments.model_graph,
        capability_path=arguments.capability,
        qualification_path=arguments.qualification,
        attention_execution_path=arguments.attention_execution,
        output=arguments.deployment,
    )
    qualification = load_layer_qualification(arguments.qualification)
    report = ProductionLayerDownstreamSimulator.load(arguments.deployment).execute()
    expected_intermediates = {
        role: record["payload_sha256"]
        for role, record in qualification["intermediates"].items()
        if role
        in {
            "attention_projected",
            "down",
            "gate",
            "gated_mlp",
            "mlp_norm",
            "post_attention",
            "silu_activation",
            "up",
        }
    }
    expected_output = qualification["output"]["hidden_1"]["payload_sha256"]
    if (
        report["intermediate_payload_sha256"] != expected_intermediates
        or report["output"]["hidden_1"]["payload_sha256"] != expected_output
        or report["saturated_element_count"]
        != {
            "projection": qualification["projection_saturated_element_count"],
            "rmsnorm": qualification["rmsnorm_saturated_element_count"],
            "vector": qualification["vector_saturated_element_count"],
        }
    ):
        raise ProductionLayerDownstreamSimulationError(
            "artifact-only downstream values differ from qualification evidence"
        )
    selected = qualification["selected_reference"]["output"]["hidden_1"]
    observed_codes = report["output"]["hidden_1"]["codes"]
    if [observed_codes[index] for index in selected["element_indices"]] != selected[
        "codes"
    ]:
        raise ProductionLayerDownstreamSimulationError(
            "artifact-only selected hidden-1 values differ from scalar evidence"
        )
    publish_layer_downstream_execution_report(report, arguments.report)
    print(f"build_id={manifest['build_id']}")
    print(f"report_id={report['report_id']}")
    print(f"hidden_1_sha256={expected_output}")
    print(f"command_count={report['command_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
