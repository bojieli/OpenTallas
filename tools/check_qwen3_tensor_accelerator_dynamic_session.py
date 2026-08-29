#!/usr/bin/env python3
"""Independently replay one complete Qwen dynamic short-generation session."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from runtime.reference.qwen_full_model import (  # noqa: E402
    QwenFullModelReferenceError,
    check_qwen_dynamic_session_execution,
    publish_qwen_dynamic_session_reference,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
REFERENCE_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_dynamic_session_reference_v1.schema.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate the explicit qualified RoPE artifact and all row-major "
            "checkpoint tensors, independently replay every dynamic transaction "
            "with persistent KV state, compare all operation events, layers, "
            "states, logits, ties, tokens, saturation and counters, and publish "
            "a separate content-addressed reference report."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--checkpoint-lock", type=Path)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument(
        "--execution-root",
        required=True,
        type=Path,
        help="directory containing session_execution.json, requests/, and executions/",
    )
    parser.add_argument("--report", required=True, type=Path)
    arguments = parser.parse_args()
    checkpoint_lock = arguments.checkpoint_lock or (
        arguments.deployment / "source/checkpoint.lock.json"
    )

    def progress(done: int, total: int, record: Mapping[str, Any]) -> None:
        print(
            f"reference_step={done - 1} complete={done}/{total} "
            f"output={record['output_token_id']} "
            f"transaction_reference_id={record['transaction_reference_id']}",
            flush=True,
        )

    try:
        report = check_qwen_dynamic_session_execution(
            snapshot=arguments.snapshot,
            checkpoint_lock_path=checkpoint_lock,
            deployment_root=arguments.deployment,
            session_path=arguments.session,
            session_execution_path=arguments.execution_root / "session_execution.json",
            requests_directory=arguments.execution_root / "requests",
            executions_directory=arguments.execution_root / "executions",
            progress=progress,
        )
        schema = load_strict_json(REFERENCE_SCHEMA)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)
        publish_qwen_dynamic_session_reference(report, arguments.report)
    except (OSError, QwenFullModelReferenceError, ValidationError) as exc:
        parser.error(str(exc))

    print(f"reference_id={report['reference_id']}")
    print(f"session_execution_id={report['session_execution_id']}")
    print(f"generated_token_ids={report['generated_token_ids']}")
    print(f"generated_text={report['decoded']['generated_text']!r}")
    print(f"step_reference_chain_sha256={report['step_reference_chain_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
