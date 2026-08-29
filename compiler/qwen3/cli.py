"""Reproducible standalone CLI for the isolated Qwen3-8B compiler path."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from compiler.frontend.checkpoint import (
    build_checkpoint_lock,
    load_checkpoint_lock,
    load_checkpoint_source,
    verify_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json

from .adapter import (
    build_official_tensor_contract,
    validate_official_checkpoint_lock,
)
from .checking import verify_deployment_artifacts, verify_physical_images
from .constants import DEFAULT_SOURCE
from .deployment import compile_official_deployment
from .graph import build_official_graph_contract
from .reference import OfficialQwen3Reference
from .runtime import Qwen3ServiceEngine
from .tokenizer import Qwen3Tokenizer


def _write_new(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))


def _token_ids(path: Path) -> list[int]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load token IDs {path}: {exc}") from exc
    if isinstance(value, dict):
        value = value.get("token_ids")
    if (
        not isinstance(value, list)
        or not value
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value)
    ):
        raise ValueError(
            "token input must be a nonempty integer array or {token_ids: [...]}"
        )
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="python3 -m compiler.qwen3",
        description="Compile and execute the pinned Qwen3-8B 8,000-token target",
    )
    commands = result.add_subparsers(dest="command", required=True)
    describe = commands.add_parser(
        "describe-tensors", help="emit all 399 official tensor roles"
    )
    describe.add_argument("--output", required=True, type=Path)
    graph = commands.add_parser(
        "describe-graph", help="emit the complete 616-node semantic graph"
    )
    graph.add_argument("--output", required=True, type=Path)
    lock = commands.add_parser(
        "lock-checkpoint", help="stream and hash the complete official snapshot"
    )
    lock.add_argument("--snapshot", required=True, type=Path)
    lock.add_argument("--output", required=True, type=Path)
    validate = commands.add_parser(
        "validate-checkpoint", help="validate an official checkpoint lock"
    )
    validate.add_argument("--lock", required=True, type=Path)
    validate.add_argument("--output", required=True, type=Path)
    verify_lock = commands.add_parser(
        "verify-checkpoint", help="rehash the snapshot against its lock"
    )
    verify_lock.add_argument("--snapshot", required=True, type=Path)
    verify_lock.add_argument("--lock", required=True, type=Path)
    compile_parser = commands.add_parser(
        "compile", help="emit all 36 stage images and executable artifacts"
    )
    compile_parser.add_argument("--snapshot", required=True, type=Path)
    compile_parser.add_argument("--lock", required=True, type=Path)
    compile_parser.add_argument("--output", required=True, type=Path)
    compile_parser.add_argument("--alignment", default=4096, type=int)
    verify_parser = commands.add_parser(
        "verify-deployment", help="rehash and inverse-check a deployment"
    )
    verify_parser.add_argument("--deployment", required=True, type=Path)
    verify_parser.add_argument("--output", required=True, type=Path)
    tokenize = commands.add_parser(
        "tokenize", help="tokenize raw text with the pinned local tokenizer"
    )
    tokenize.add_argument("--deployment", required=True, type=Path)
    tokenize.add_argument("--text", required=True)
    tokenize.add_argument("--output", required=True, type=Path)
    run = commands.add_parser(
        "run", help="run full prefill and greedy decode from compiled artifacts"
    )
    run.add_argument("--deployment", required=True, type=Path)
    token_group = run.add_mutually_exclusive_group(required=True)
    token_group.add_argument("--tokens", type=Path)
    token_group.add_argument("--text")
    token_group.add_argument("--messages", type=Path)
    run.add_argument("--max-new-tokens", default=1, type=int)
    run.add_argument("--device", default="cuda")
    run.add_argument("--attention-backend", choices=("sdpa", "eager"), default="sdpa")
    run.add_argument("--capture-layer-hashes", action="store_true")
    run.add_argument("--output", required=True, type=Path)
    reference = commands.add_parser(
        "reference-run", help="run pinned official Transformers source"
    )
    reference.add_argument("--snapshot", required=True, type=Path)
    reference.add_argument("--tokens", required=True, type=Path)
    reference.add_argument("--device", default="cuda")
    reference.add_argument(
        "--attention-backend", choices=("sdpa", "eager"), default="sdpa"
    )
    reference.add_argument("--capture-layer-hashes", action="store_true")
    reference.add_argument("--output", required=True, type=Path)
    return result


def _progress(done: int, total: int, name: str) -> None:
    if done == 1 or done % 25 == 0 or done == total:
        print(f"[{done:03d}/{total:03d}] {name}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "describe-tensors":
            contract = build_official_tensor_contract()
            _write_new(arguments.output, contract)
            print(contract["contract_id"])
        elif arguments.command == "describe-graph":
            graph = build_official_graph_contract()
            _write_new(arguments.output, graph)
            print(graph["graph_id"])
        elif arguments.command == "lock-checkpoint":
            source = load_checkpoint_source(DEFAULT_SOURCE)
            lock = build_checkpoint_lock(arguments.snapshot, source)
            _write_new(arguments.output, lock)
            print(lock["lock_id"])
        elif arguments.command == "validate-checkpoint":
            validation = validate_official_checkpoint_lock(
                load_checkpoint_lock(arguments.lock)
            )
            _write_new(arguments.output, validation)
            print(validation["validation_id"])
        elif arguments.command == "verify-checkpoint":
            lock = load_checkpoint_lock(arguments.lock)
            verify_checkpoint_lock(arguments.snapshot, lock)
            print(lock["lock_id"])
        elif arguments.command == "compile":
            manifest = compile_official_deployment(
                snapshot=arguments.snapshot,
                lock=load_checkpoint_lock(arguments.lock),
                output=arguments.output,
                alignment=arguments.alignment,
                progress=_progress,
            )
            print(manifest["build_id"])
        elif arguments.command == "verify-deployment":
            root = arguments.deployment.resolve()
            manifest = load_strict_json(root / "deployment_manifest.json")
            verify_deployment_artifacts(root, manifest)
            lock = load_checkpoint_lock(root / "checkpoint.lock.json")
            physical = load_strict_json(root / "physical/physical_map.json")
            inverse = verify_physical_images(root, physical, lock)
            engine = Qwen3ServiceEngine(root, device="cpu", verify_artifacts=False)
            report_body = {
                "artifact_count": len(manifest["artifacts"]),
                "build_id": manifest["build_id"],
                "inverse_report_id": inverse["report_id"],
                "schedule_certificate_id": engine.schedule_certificate[
                    "certificate_id"
                ],
                "schema": "opentallas.qwen3.deployment_verification.v1",
                "status": "pass",
            }
            report = {
                **report_body,
                "report_id": hashlib.sha256(
                    canonical_json_bytes(report_body)
                ).hexdigest(),
            }
            _write_new(arguments.output, report)
            print(report["report_id"])
        elif arguments.command == "tokenize":
            tokenizer = Qwen3Tokenizer(arguments.deployment)
            ids = tokenizer.encode(arguments.text)
            _write_new(
                arguments.output,
                {"schema": "opentallas.qwen3.tokens.v1", "token_ids": ids},
            )
            print(len(ids))
        elif arguments.command == "run":
            tokenizer = None
            if arguments.tokens is not None:
                ids = _token_ids(arguments.tokens)
            else:
                tokenizer = Qwen3Tokenizer(arguments.deployment)
                if arguments.text is not None:
                    ids = tokenizer.encode(arguments.text)
                else:
                    messages = load_strict_json(arguments.messages)
                    raw_messages = messages.get("messages")
                    ids = tokenizer.encode_chat(raw_messages)
            engine = Qwen3ServiceEngine(
                arguments.deployment,
                device=arguments.device,
                attention_backend=arguments.attention_backend,
            )
            result = engine.generate_greedy(
                ids,
                max_new_tokens=arguments.max_new_tokens,
                capture_layer_hashes=arguments.capture_layer_hashes,
            )
            if tokenizer is not None:
                try:
                    result["generated_text"] = tokenizer.decode(
                        result["generated_token_ids"]
                    )
                except Exception:
                    result["generated_text"] = None
                result_body = {
                    key: value for key, value in result.items() if key != "result_id"
                }
                result["result_id"] = hashlib.sha256(
                    canonical_json_bytes(result_body)
                ).hexdigest()
            _write_new(arguments.output, result)
            print(result["result_id"])
        elif arguments.command == "reference-run":
            reference = OfficialQwen3Reference(
                arguments.snapshot,
                device=arguments.device,
                attention_backend=arguments.attention_backend,
            )
            result = reference.run_span(
                _token_ids(arguments.tokens),
                capture_layer_hashes=arguments.capture_layer_hashes,
            )
            _write_new(arguments.output, result.report)
            print(result.report["report_id"])
        else:
            raise ValueError(f"unsupported command {arguments.command!r}")
        return 0
    except Exception as exc:
        print(f"qwen3: {exc}", file=sys.stderr)
        return 2


__all__ = ["main", "parser"]
