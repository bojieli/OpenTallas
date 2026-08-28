"""OpenTallas compiler command line."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from compiler.build import BuildError, build_deployment
from compiler.checking.inverse import InverseCheckError
from compiler.frontend.checkpoint import (
    CheckpointError,
    build_checkpoint_lock,
    load_checkpoint_lock,
    load_checkpoint_source,
    verify_checkpoint_lock,
)
from compiler.image.rom import RomImageError
from compiler.ir.model import IRValidationError, canonical_json_bytes
from compiler.microcode.isa import MicrocodeError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="python3 -m compiler.cli",
        description="Build deterministic OpenTallas executable-system artifacts.",
    )
    subparsers = result.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser(
        "compile", help="compile one strict semantic IR deployment"
    )
    compile_parser.add_argument("--model", required=True, type=Path)
    compile_parser.add_argument("--output", required=True, type=Path)
    lock_parser = subparsers.add_parser(
        "lock-checkpoint",
        help="stream and content-lock a complete local safetensors checkpoint",
    )
    lock_parser.add_argument("--source", required=True, type=Path)
    lock_parser.add_argument("--snapshot", required=True, type=Path)
    lock_parser.add_argument("--output", required=True, type=Path)
    verify_parser = subparsers.add_parser(
        "verify-checkpoint",
        help="replay a checkpoint lock against every local checkpoint byte",
    )
    verify_parser.add_argument("--lock", required=True, type=Path)
    verify_parser.add_argument("--snapshot", required=True, type=Path)
    return result


def _write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_json_bytes(value))
    except FileExistsError as exc:
        raise CheckpointError(f"output already exists: {path}") from exc


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "compile":
            manifest = build_deployment(arguments.model, arguments.output)
            print(
                f"built {manifest['model_id']} deployment {manifest['build_id']} "
                f"at {arguments.output.resolve()}"
            )
            return 0
        if arguments.command == "lock-checkpoint":
            source = load_checkpoint_source(arguments.source)
            lock = build_checkpoint_lock(arguments.snapshot, source)
            _write_new_json(arguments.output, lock)
            summary = lock["checkpoint"]
            print(
                f"locked {summary['tensor_count']} tensors in "
                f"{summary['shard_count']} shards ({summary['payload_bytes']} bytes); "
                f"lock {lock['lock_id']}"
            )
            return 0
        if arguments.command == "verify-checkpoint":
            lock = load_checkpoint_lock(arguments.lock)
            verify_checkpoint_lock(arguments.snapshot, lock)
            print(f"verified checkpoint lock {lock['lock_id']}")
            return 0
    except (
        BuildError,
        IRValidationError,
        RomImageError,
        MicrocodeError,
        InverseCheckError,
        CheckpointError,
        OSError,
    ) as exc:
        print(f"compiler error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("argparse accepted an unknown command")
