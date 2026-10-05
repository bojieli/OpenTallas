#!/usr/bin/env python3
"""Retain the byte-exact Qwen interrupted-versus-uninterrupted differential."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, SchemaError, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from runtime.tensor_accelerator.qwen_full_model_restart import (  # noqa: E402
    QwenRestartDifferentialError,
    publish_restart_differential,
)


SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_restart_differential_v1.schema.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate two full-model transactions, the intervening runtime "
            "checkpoint, and a separately run uninterrupted comparator; require "
            "byte-exact requests, reports, counters, logits, state, and final "
            "checkpoint before atomically retaining the evidence."
        )
    )
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--interrupted", required=True, type=Path)
    parser.add_argument("--uninterrupted", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        schema = load_strict_json(SCHEMA)
        Draft202012Validator.check_schema(schema)
        report = publish_restart_differential(
            session_path=arguments.session,
            interrupted_root=arguments.interrupted,
            uninterrupted_root=arguments.uninterrupted,
            repository_root=ROOT,
            output=arguments.output,
        )
        Draft202012Validator(schema).validate(report)
    except (
        OSError,
        QwenRestartDifferentialError,
        SchemaError,
        ValidationError,
    ) as exc:
        parser.error(str(exc))
    print(f"status={report['status']}")
    print(f"differential_id={report['differential_id']}")
    print(
        "restart_checkpoint_id="
        f"{report['checkpoint_restore']['checkpoint_id']}"
    )
    print(f"final_checkpoint_id={report['final_checkpoint']['checkpoint_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
