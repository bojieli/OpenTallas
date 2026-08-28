#!/usr/bin/env python3
"""Build, independently check, and execute real Qwen embedding RMSNorm."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.production_rmsnorm import (  # noqa: E402
    build_rmsnorm_deployment,
)
from compiler.tensor_accelerator.rmsnorm_qualification import (  # noqa: E402
    load_rmsnorm_qualification,
)
from runtime.tensor_accelerator.production_rmsnorm_simulator import (  # noqa: E402
    ProductionRMSNormSimulationError,
    ProductionRMSNormSimulator,
    publish_rmsnorm_execution_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile and causally execute an authenticated Qwen token embedding "
            "through layer-0 input RMSNorm on the HBM/SRAM tensor accelerator."
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

    manifest = build_rmsnorm_deployment(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        model_graph_path=arguments.model_graph,
        capability_path=arguments.capability,
        qualification_path=arguments.qualification,
        output=arguments.deployment,
    )
    qualification = load_rmsnorm_qualification(arguments.qualification)
    report = ProductionRMSNormSimulator.load(arguments.deployment).execute()
    if (
        report["output"]["payload_sha256"]
        != qualification["output"]["payload_sha256"]
        or report["output"]["normalized_payload_sha256"]
        != qualification["output"]["normalized_payload_sha256"]
        or report["output"]["saturated_element_count"]
        != qualification["output"]["saturated_element_count"]
        or report["output"]["normalized_saturated_element_count"]
        != qualification["output"]["normalized_saturated_element_count"]
    ):
        raise ProductionRMSNormSimulationError(
            "artifact-only output differs from qualification evidence"
        )
    selected = qualification["selected_reference"]
    observed = [
        report["output"]["codes"][index]
        for index in selected["element_indices"]
    ]
    if observed != selected["output_codes"]:
        raise ProductionRMSNormSimulationError(
            "artifact-only selected outputs differ from scalar reference evidence"
        )
    publish_rmsnorm_execution_report(report, arguments.report)
    print(f"build_id={manifest['build_id']}")
    print(f"report_id={report['report_id']}")
    print(f"output_sha256={report['output']['payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
