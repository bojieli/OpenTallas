#!/usr/bin/env python3
"""Compile a tokenizer prompt into a versioned Qwen dynamic session."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from compiler.tensor_accelerator.qwen_full_model_dynamic import (  # noqa: E402
    QwenDynamicArtifactError,
    build_dynamic_request,
    build_dynamic_session,
    publish_dynamic_request,
    publish_dynamic_session,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
SESSION_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_dynamic_session_v1.schema.json"
)
REQUEST_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_dynamic_request_v1.schema.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate the pinned Qwen tokenizer and deployment, tokenize a "
            "real prompt exactly, and emit a content-addressed short-generation "
            "session plus its first causal request. This does not execute the model."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--checkpoint-lock", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--generated-tokens", type=int, default=32)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--initial-request", required=True, type=Path)
    arguments = parser.parse_args()

    try:
        session = build_dynamic_session(
            snapshot=arguments.snapshot,
            checkpoint_lock_path=arguments.checkpoint_lock,
            model_graph_path=arguments.deployment / "source/model_graph.v2.json",
            deployment_manifest_path=arguments.deployment / "deployment_manifest.json",
            physical_plan_path=arguments.deployment / "physical/physical_plan.json",
            prompt_text=arguments.prompt,
            generated_token_limit=arguments.generated_tokens,
        )
        request = build_dynamic_request(session)
        for value, path in (
            (session, SESSION_SCHEMA),
            (request, REQUEST_SCHEMA),
        ):
            schema = load_strict_json(path)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(value)
        publish_dynamic_session(session, arguments.session)
        publish_dynamic_request(request, session, None, arguments.initial_request)
    except (OSError, QwenDynamicArtifactError, ValidationError) as exc:
        parser.error(str(exc))

    print(f"session_id={session['session_id']}")
    print(f"prompt_token_ids={session['prompt']['token_ids']}")
    print(f"generated_token_limit={session['generation']['generated_token_limit']}")
    print(f"initial_request_id={request['request_id']}")
    print(f"initial_transaction_id={request['transaction_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
