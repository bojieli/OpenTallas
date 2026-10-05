#!/usr/bin/env python3
"""Build the committed Qwen 8,000+32 acceptance session and first request."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from compiler.tensor_accelerator.qwen_full_model_long_acceptance import (  # noqa: E402
    QwenLongAcceptanceArtifactError,
    build_long_acceptance_request,
    build_long_acceptance_session,
    publish_long_acceptance_request,
    publish_long_acceptance_session,
)


DEFAULT_DEPLOYMENT = (
    ROOT / "results/tensor_accelerator/qwen3_long_acceptance_physical_v1"
)
SESSION_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_long_acceptance_session_v1.schema.json"
)
REQUEST_SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_long_acceptance_request_v1.schema.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Authenticate the governed Qwen workload manifest and release report "
            "directly from their immutable Git commit, bind the V7 8,192-row "
            "deployment, and publish the exact 8,000-token-ID plus 32-decision "
            "session. This does not execute the model."
        )
    )
    parser.add_argument("--fixture-repository", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--initial-request", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        session = build_long_acceptance_session(
            deployment_root=arguments.deployment,
            fixture_repository=arguments.fixture_repository,
        )
        request = build_long_acceptance_request(session)
        for value, path in (
            (session, SESSION_SCHEMA),
            (request, REQUEST_SCHEMA),
        ):
            schema = load_strict_json(path)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(value)
        publish_long_acceptance_session(session, arguments.session)
        publish_long_acceptance_request(
            request, session, None, arguments.initial_request
        )
    except (OSError, QwenLongAcceptanceArtifactError, ValidationError) as exc:
        parser.error(str(exc))
    print(f"session_id={session['session_id']}")
    print(f"fixture_commit={session['workload_fixture']['commit']}")
    print(f"prompt_encoding={session['prompt']['encoding']}")
    print(f"prompt_token_count={session['prompt']['token_count']}")
    print(f"prompt_token_id={session['prompt']['token_id']}")
    print(f"prompt_token_ids_sha256={session['prompt']['token_ids_sha256']}")
    print(f"generated_token_limit={session['generation']['generated_token_limit']}")
    print(f"context_capacity={session['context_capacity']}")
    print(f"initial_request_id={request['request_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
