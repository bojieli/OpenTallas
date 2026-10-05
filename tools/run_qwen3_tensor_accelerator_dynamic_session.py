#!/usr/bin/env python3
"""Run one complete versioned Qwen short-generation session artifact-only."""

from __future__ import annotations

from pathlib import Path
import sys

from jsonschema import Draft202012Validator, ValidationError
from tokenizers import Tokenizer, __version__ as tokenizers_version


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import load_strict_json, sha256_file  # noqa: E402
from compiler.tensor_accelerator.qwen_full_model_dynamic import (  # noqa: E402
    QwenDynamicArtifactError,
    build_dynamic_request,
    build_dynamic_session_execution,
    publish_dynamic_request,
    publish_dynamic_session_execution,
    validate_dynamic_request,
    validate_dynamic_session,
)
from runtime.tensor_accelerator.qwen_full_model_simulator import (  # noqa: E402
    QwenFullModelSimulationError,
    QwenFullModelSimulator,
    publish_qwen_full_model_dynamic_execution_report,
)


DEFAULT_DEPLOYMENT = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
DYNAMIC_EXECUTION_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_dynamic_execution_v1.schema.json"
)
SESSION_EXECUTION_SCHEMA = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_full_model_dynamic_session_execution_v1.schema.json"
)


def _tokenizer(snapshot: Path, session: dict[str, object]) -> Tokenizer:
    record = session["tokenizer"]
    path = Path(snapshot) / record["path"]
    digest, size = sha256_file(path)
    if (
        tokenizers_version != record["library_version"]
        or digest != record["sha256"]
        or size < 1
    ):
        raise QwenFullModelSimulationError(
            "dynamic session tokenizer does not match its immutable manifest"
        )
    tokenizer = Tokenizer.from_file(str(path))
    if tokenizer.get_vocab_size(with_added_tokens=True) != 151_669:
        raise QwenFullModelSimulationError(
            "dynamic session tokenizer vocabulary differs"
        )
    return tokenizer


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Authenticate all retained HBM shards once, execute the complete "
            "924,386-command Qwen program for every causal prompt/decode "
            "transaction, and retain a chained 32-generated-token report. The "
            "aggregate report does not claim target-reference, timing, or "
            "8,000-token closure."
        )
    )
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="session artifact directory containing requests/ and executions/",
    )
    arguments = parser.parse_args()

    try:
        session = validate_dynamic_session(load_strict_json(arguments.session))
        transaction_schema = load_strict_json(DYNAMIC_EXECUTION_SCHEMA)
        session_schema = load_strict_json(SESSION_EXECUTION_SCHEMA)
        Draft202012Validator.check_schema(transaction_schema)
        Draft202012Validator.check_schema(session_schema)
        transaction_validator = Draft202012Validator(transaction_schema)
        session_validator = Draft202012Validator(session_schema)
        tokenizer = _tokenizer(arguments.snapshot, session)
        prompt_count = session["prompt"]["token_count"]
        generated_limit = session["generation"]["generated_token_limit"]
        expected_transactions = prompt_count + generated_limit - 1
        previous: dict[str, object] | None = None
        requests: list[dict[str, object]] = []
        reports: list[dict[str, object]] = []
        generated_tokens: list[int] = []

        with QwenFullModelSimulator.load(
            arguments.deployment, verify_hbm_hashes=True
        ) as simulator:
            simulator.begin_dynamic_session(arguments.session)
            for step in range(expected_transactions):
                request_path = arguments.output / f"requests/request.{step:04d}.json"
                if step == 0:
                    request = validate_dynamic_request(
                        load_strict_json(request_path), session, None
                    )
                else:
                    request = build_dynamic_request(session, previous)
                    publish_dynamic_request(request, session, previous, request_path)
                report = simulator.execute_dynamic(request_path)
                transaction_validator.validate(report)
                report_path = arguments.output / f"executions/execution.{step:04d}.json"
                publish_qwen_full_model_dynamic_execution_report(report, report_path)
                token = report["outputs"]["committed_logits"]["greedy_token_id"]
                if request["output_role"] == "generated_token":
                    generated_tokens.append(token)
                    if token in session["generation"]["eos_token_ids"]:
                        raise QwenFullModelSimulationError(
                            "dynamic session encountered an unexpected early EOS"
                        )
                requests.append(request)
                reports.append(report)
                previous = report
                print(
                    f"step={step} generated={len(generated_tokens)} "
                    f"input={request['token_id']} output={token} "
                    f"report_id={report['report_id']}",
                    flush=True,
                )

        if len(generated_tokens) != generated_limit or previous is None:
            raise QwenFullModelSimulationError(
                "dynamic session did not produce the frozen generated-token count"
            )
        result = build_dynamic_session_execution(
            session,
            requests,
            reports,
            decode_token_ids=lambda token_ids: tokenizer.decode(
                token_ids, skip_special_tokens=False
            ),
        )
        session_validator.validate(result)
        output = arguments.output / "session_execution.json"
        publish_dynamic_session_execution(result, session, output)
    except (
        OSError,
        QwenDynamicArtifactError,
        QwenFullModelSimulationError,
        ValidationError,
    ) as exc:
        parser.error(str(exc))

    print(f"session_execution_id={result['session_execution_id']}")
    print(f"generated_token_ids={result['generated_token_ids']}")
    print(f"generated_text={result['decoded']['generated_text']!r}")
    print(f"aggregate_counter_sha256={result['aggregate_counter_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
