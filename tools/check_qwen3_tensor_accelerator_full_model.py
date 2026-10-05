#!/usr/bin/env python3
"""Independently reproduce one complete Qwen artifact-only execution."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from runtime.reference.qwen_full_model import (  # noqa: E402
    QwenFullModelReferenceError,
    check_qwen_full_model_execution,
    publish_qwen_full_model_reference,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
DEFAULT_EXECUTION_REPORT = (
    ROOT / "results/tensor_accelerator/qwen3_full_model_execution_v1.json"
)
REFERENCE_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_full_model_reference_v1.schema.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read the immutable row-major Qwen3-8B checkpoint, independently "
            "execute every one of the 617 target-precision operations using "
            "segmented-K matrix arithmetic and scalar kernel references, and "
            "compare every event, layer, state, logit, token, saturation value, "
            "and counter with one retained artifact-only simulator report."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--checkpoint-lock", required=True, type=Path)
    parser.add_argument(
        "--deployment",
        type=Path,
        default=DEFAULT_DEPLOYMENT,
        help="retained complete-model deployment containing source contracts",
    )
    parser.add_argument(
        "--model-graph",
        type=Path,
        help="model graph override; omitted uses deployment/source/model_graph.v2.json",
    )
    parser.add_argument(
        "--capability",
        type=Path,
        help="capability override; omitted uses deployment/capability.json",
    )
    parser.add_argument(
        "--request",
        type=Path,
        help=(
            "fixed request override; omitted uses "
            "deployment/request/execution_request.json"
        ),
    )
    parser.add_argument(
        "--execution-report",
        type=Path,
        default=DEFAULT_EXECUTION_REPORT,
        help="canonical artifact-only simulator report to reproduce",
    )
    parser.add_argument(
        "--report",
        required=True,
        type=Path,
        help="new path for the canonical independent-reference report",
    )
    arguments = parser.parse_args()

    model_graph = arguments.model_graph or (
        arguments.deployment / "source/model_graph.v2.json"
    )
    capability = arguments.capability or arguments.deployment / "capability.json"
    request = arguments.request or (
        arguments.deployment / "request/execution_request.json"
    )
    try:
        report = check_qwen_full_model_execution(
            snapshot=arguments.snapshot,
            checkpoint_lock_path=arguments.checkpoint_lock,
            model_graph_path=model_graph,
            capability_path=capability,
            request_path=request,
            execution_report_path=arguments.execution_report,
        )
        schema = load_strict_json(REFERENCE_SCHEMA)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)
        publish_qwen_full_model_reference(report, arguments.report)
    except (OSError, QwenFullModelReferenceError, ValidationError) as exc:
        parser.error(str(exc))

    print(f"reference_id={report['reference_id']}")
    print(f"execution_report_id={report['execution_report_id']}")
    print(f"hidden_36_sha256={report['outputs']['hidden_36']['payload_sha256']}")
    print(f"logits_sha256={report['outputs']['committed_logits']['payload_sha256']}")
    print(f"greedy_token_id={report['outputs']['committed_logits']['greedy_token_id']}")
    print(f"counter_sha256={report['counter_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
