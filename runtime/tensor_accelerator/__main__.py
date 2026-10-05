"""Command-line entry point for artifact-only tensor-accelerator simulation."""

from __future__ import annotations

import argparse
from pathlib import Path

from compiler.tensor_accelerator.common import canonical_json_bytes

from .simulator import TensorAcceleratorSimulator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute a compiled tensor-accelerator deployment."
    )
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=("functional", "data_bearing_timing"),
        default="data_bearing_timing",
    )
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error(f"output already exists: {arguments.output}")
    result = TensorAcceleratorSimulator.load(arguments.deployment).execute(
        arguments.request,
        mode=arguments.mode,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_json_bytes(result))
        handle.flush()
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
