#!/usr/bin/env python3
"""Build, independently check, and execute the real Qwen projection slice."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.bf16_qualification import (  # noqa: E402
    load_qualification_report,
)
from compiler.tensor_accelerator.production_projection import (  # noqa: E402
    build_projection_deployment,
)
from runtime.tensor_accelerator.production_simulator import (  # noqa: E402
    ProductionProjectionSimulator,
    ProductionSimulationError,
    publish_execution_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile and causally execute a qualification-bound Qwen BF16 "
            "projection on the HBM/SRAM tensor accelerator."
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

    manifest = build_projection_deployment(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        model_graph_path=arguments.model_graph,
        capability_path=arguments.capability,
        qualification_path=arguments.qualification,
        output=arguments.deployment,
    )
    qualification = load_qualification_report(arguments.qualification)
    report = ProductionProjectionSimulator.load(arguments.deployment).execute()
    if (
        report["output"]["payload_sha256"]
        != qualification["output"]["payload_sha256"]
        or report["output"]["saturated_element_count"]
        != qualification["output"]["saturated_element_count"]
    ):
        raise ProductionSimulationError(
            "artifact-only output differs from qualification evidence"
        )
    selected = qualification["selected_reference"]
    observed = [report["output"]["codes"][index] for index in selected["output_rows"]]
    if observed != selected["output_codes"]:
        raise ProductionSimulationError(
            "artifact-only selected outputs differ from scalar reference evidence"
        )
    publish_execution_report(report, arguments.report)
    print(f"build_id={manifest['build_id']}")
    print(f"report_id={report['report_id']}")
    print(f"output_sha256={report['output']['payload_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
