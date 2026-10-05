#!/usr/bin/env python3
"""Run multiple compiled Qwen3 questions until EOS or the 8K context limit."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any

from jsonschema import Draft202012Validator
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.ir.model import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)
from compiler.qwen3.constants import SCHEMA_DIR, TARGET_CONTEXT_TOKENS  # noqa: E402
from compiler.qwen3.runtime import Qwen3ServiceEngine  # noqa: E402
from compiler.qwen3.tokenizer import Qwen3Tokenizer  # noqa: E402


SUITE_SCHEMA = "opentallas.qwen3.eos_question_suite.v1"
CAMPAIGN_SCHEMA = "opentallas.qwen3.eos_campaign.v1"
GENERATION_SCHEMA = "opentallas.qwen3.generation_result.v1"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Require compiled Qwen3-8B to reach EOS on multiple questions"
    )
    result.add_argument("--deployment", required=True, type=Path)
    result.add_argument("--suite", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--device", default="cuda")
    result.add_argument(
        "--attention-backend", choices=("sdpa", "eager"), default="sdpa"
    )
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _body_id(value: dict[str, Any], identity: str) -> str:
    body = {key: item for key, item in value.items() if key != identity}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _load_schema(name: str) -> dict[str, Any]:
    schema = load_strict_json(SCHEMA_DIR / name)
    Draft202012Validator.check_schema(schema)
    return schema


def _write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def _load_suite(path: Path) -> dict[str, Any]:
    suite = load_strict_json(path)
    Draft202012Validator(_load_schema("eos_question_suite_v1.schema.json")).validate(
        suite
    )
    if suite["schema"] != SUITE_SCHEMA:
        raise ValueError("question suite schema differs")
    if suite["suite_id"] != _body_id(suite, "suite_id"):
        raise ValueError("suite_id does not bind the question suite")
    identifiers = [question["id"] for question in suite["questions"]]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("question identifiers must be unique")
    return suite


def _generation_with_text(
    engine: Qwen3ServiceEngine,
    tokenizer: Qwen3Tokenizer,
    prompt_ids: list[int],
    *,
    maximum_new_tokens: int,
    eos_token_ids: list[int],
) -> dict[str, Any]:
    generation = engine.generate_greedy(
        prompt_ids,
        max_new_tokens=maximum_new_tokens,
        eos_token_ids=eos_token_ids,
        capture_layer_hashes=False,
    )
    generation["generated_text"] = tokenizer.decode(
        generation["generated_token_ids"], skip_special_tokens=False
    )
    generation["result_id"] = _body_id(generation, "result_id")
    Draft202012Validator(_load_schema("generation_result_v1.schema.json")).validate(
        generation
    )
    return generation


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    output = arguments.output.resolve()
    if output.exists():
        parser().error(f"--output already exists: {output}")
    suite = _load_suite(arguments.suite)
    if suite["maximum_new_tokens"] != TARGET_CONTEXT_TOKENS:
        parser().error("suite maximum_new_tokens must equal 8000")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    engine: Qwen3ServiceEngine | None = None
    campaign_started = time.monotonic()
    try:
        tokenizer = Qwen3Tokenizer(arguments.deployment)
        engine = Qwen3ServiceEngine(
            arguments.deployment,
            device=arguments.device,
            attention_backend=arguments.attention_backend,
        )
        eos_token_ids = list(suite["eos_token_ids"])
        summaries: list[dict[str, Any]] = []
        for ordinal, question in enumerate(suite["questions"], start=1):
            prompt_ids = tokenizer.encode_chat(
                question["messages"],
                enable_thinking=question["enable_thinking"],
            )
            effective_maximum = min(
                int(suite["maximum_new_tokens"]),
                TARGET_CONTEXT_TOKENS - len(prompt_ids) + 1,
            )
            if effective_maximum <= 0:
                raise ValueError(
                    f"question {question['id']!r} leaves no decode capacity"
                )
            print(
                f"[{ordinal}/{len(suite['questions'])}] {question['id']}: "
                f"prompt={len(prompt_ids)} effective_max={effective_maximum}",
                file=sys.stderr,
                flush=True,
            )
            started = time.monotonic()
            generation = _generation_with_text(
                engine,
                tokenizer,
                prompt_ids,
                maximum_new_tokens=effective_maximum,
                eos_token_ids=eos_token_ids,
            )
            elapsed = round(time.monotonic() - started, 6)
            reached_eos = (
                generation["termination"] == "eos"
                and generation["generated_token_ids"][-1] in eos_token_ids
            )
            relative = f"questions/{question['id']}.json"
            _write_new(temporary / relative, generation)
            generated_count = len(generation["generated_token_ids"])
            summaries.append(
                {
                    "context_tokens_committed": generation["context_tokens_committed"],
                    "effective_maximum_new_tokens": effective_maximum,
                    "enable_thinking": question["enable_thinking"],
                    "eos_token_id": (
                        generation["generated_token_ids"][-1] if reached_eos else None
                    ),
                    "generated_token_count": generated_count,
                    "id": question["id"],
                    "prompt_token_count": len(prompt_ids),
                    "prompt_token_sha256": hashlib.sha256(
                        canonical_json_bytes(prompt_ids)
                    ).hexdigest(),
                    "reached_eos_within_warning_threshold": (
                        reached_eos
                        and generated_count <= suite["warning_token_threshold"]
                    ),
                    "result_id": generation["result_id"],
                    "result_path": relative,
                    "span_count": len(generation["spans"]),
                    "termination": "eos" if reached_eos else "context_limit",
                    "wall_time_seconds": elapsed,
                }
            )
            print(
                f"[{ordinal}/{len(suite['questions'])}] {question['id']}: "
                f"termination={summaries[-1]['termination']} "
                f"generated={generated_count} elapsed={elapsed:.3f}s",
                file=sys.stderr,
                flush=True,
            )
        all_reached_eos = all(item["termination"] == "eos" for item in summaries)
        if arguments.device.startswith("cuda"):
            device_name = torch.cuda.get_device_name(torch.device(arguments.device))
        else:
            device_name = "cpu"
        body = {
            "all_reached_eos": all_reached_eos,
            "attention_backend": arguments.attention_backend,
            "build_id": engine.manifest["build_id"],
            "context_limit_tokens": TARGET_CONTEXT_TOKENS,
            "device": str(engine.device),
            "device_name": device_name,
            "eos_token_ids": eos_token_ids,
            "maximum_new_tokens": suite["maximum_new_tokens"],
            "question_count": len(summaries),
            "questions": summaries,
            "runner_sha256": _sha256_file(Path(__file__)),
            "schema": CAMPAIGN_SCHEMA,
            "status": "pass" if all_reached_eos else "fail",
            "suite_id": suite["suite_id"],
            "torch_version": torch.__version__,
            "total_wall_time_seconds": round(time.monotonic() - campaign_started, 6),
            "warning_token_threshold": suite["warning_token_threshold"],
        }
        report = {
            **body,
            "report_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
        }
        Draft202012Validator(_load_schema("eos_campaign_v1.schema.json")).validate(
            report
        )
        _write_new(temporary / "campaign.json", report)
        temporary.rename(output)
        print(report["report_id"])
        return 0 if all_reached_eos else 1
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    finally:
        if engine is not None:
            engine.close()


if __name__ == "__main__":
    raise SystemExit(main())
