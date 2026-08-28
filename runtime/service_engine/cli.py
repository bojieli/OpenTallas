"""Command line for the functional service engine."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from compiler.ir.model import IRValidationError, write_canonical_json
from compiler.microcode.isa import MicrocodeError
from runtime.service_engine.interpreter import ServiceEngineError, execute_deployment


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
        result = execute_deployment(arguments.deployment, arguments.inputs)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        write_canonical_json(arguments.output, result)
    except (ServiceEngineError, IRValidationError, MicrocodeError, OSError) as exc:
        print(f"service-engine error: {exc}", file=sys.stderr)
        return 2
    print(
        f"executed {result['model_id']} deployment {result['build_id']}; "
        f"counters reconcile exactly"
    )
    return 0
