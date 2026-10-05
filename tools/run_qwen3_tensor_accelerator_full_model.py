#!/usr/bin/env python3
"""Execute the retained complete Qwen deployment from artifacts and real data."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from runtime.tensor_accelerator.qwen_full_model_simulator import (  # noqa: E402
    QwenFullModelSimulationError,
    QwenFullModelSimulator,
    publish_qwen_full_model_execution_report,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
REPORT_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_execution_v1.schema.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate every retained HBM shard and execute one complete "
            "Qwen3-8B token through all 617 compiled operations, 36 layers, "
            "full logits, greedy selection, and atomic 36-resource KV commit. "
            "This is full artifact-driven data-bearing functional execution; "
            "it is not a timing or 8,000-token acceptance claim."
        )
    )
    parser.add_argument(
        "--deployment",
        type=Path,
        default=DEFAULT_DEPLOYMENT,
        help="published complete-model physical deployment",
    )
    parser.add_argument(
        "--request",
        type=Path,
        help=(
            "canonical execution request; omitted uses the fixed request v1 "
            "bound into the deployment"
        ),
    )
    parser.add_argument(
        "--report",
        required=True,
        type=Path,
        help="new path for the canonical execution report",
    )
    arguments = parser.parse_args()

    try:
        with QwenFullModelSimulator.load(
            arguments.deployment,
            verify_hbm_hashes=True,
        ) as simulator:
            report = simulator.execute(arguments.request)
        schema = load_strict_json(REPORT_SCHEMA)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)
        publish_qwen_full_model_execution_report(report, arguments.report)
    except (
        OSError,
        QwenFullModelSimulationError,
        ValidationError,
    ) as exc:
        parser.error(str(exc))

    print(f"build_id={report['build_id']}")
    print(f"report_id={report['report_id']}")
    print(f"hidden_36_sha256={report['outputs']['hidden_36']['payload_sha256']}")
    print(f"logits_sha256={report['outputs']['committed_logits']['payload_sha256']}")
    print(f"greedy_token_id={report['outputs']['committed_logits']['greedy_token_id']}")
    print(f"command_count={report['command_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
