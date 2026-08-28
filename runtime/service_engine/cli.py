"""Command line for the functional service engine."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from compiler.ir.model import IRValidationError, canonical_json_bytes, load_strict_json
from compiler.microcode.isa import MicrocodeError
from runtime.service_engine.deepseek_v4_lookup import (
    DEPLOYMENT_SCHEMA as DEEPSEEK_V4_LOOKUP_DEPLOYMENT_SCHEMA,
)
from runtime.service_engine.deepseek_v4_lookup import (
    DeepSeekV4LookupServiceEngineError,
    execute_deepseek_v4_lookup_deployment,
)
from runtime.service_engine.interpreter import ServiceEngineError, execute_deployment


def _execute(deployment: Path, inputs: Path) -> dict[str, object]:
    manifest = load_strict_json(deployment / "deployment_manifest.json")
    if manifest.get("schema") == DEEPSEEK_V4_LOOKUP_DEPLOYMENT_SCHEMA:
        return execute_deepseek_v4_lookup_deployment(deployment, inputs)
    return execute_deployment(deployment, inputs)


def _write_new(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_json_bytes(result))
    except FileExistsError as exc:
        raise ServiceEngineError(f"output already exists: {path}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m runtime.service_engine",
        description="Execute a verified OpenTallas deployment in software.",
    )
    parser.add_argument("--deployment", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args(argv)
    if arguments.output.exists():
        print(f"service-engine error: output already exists: {arguments.output}", file=sys.stderr)
        return 2
    try:
        result = _execute(arguments.deployment, arguments.inputs)
        _write_new(arguments.output, result)
    except (
        DeepSeekV4LookupServiceEngineError,
        ServiceEngineError,
        IRValidationError,
        MicrocodeError,
        OSError,
    ) as exc:
        print(f"service-engine error: {exc}", file=sys.stderr)
        return 2
    print(
        f"executed {result['model_id']} deployment {result['build_id']}; "
        f"counters reconcile exactly"
    )
    return 0
