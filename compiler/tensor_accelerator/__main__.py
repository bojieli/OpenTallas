"""Command-line entry point for deterministic tensor-accelerator compilation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .build import build_deployment


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile a Model Graph into an HBM/SRAM tensor-accelerator deployment."
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    manifest = build_deployment(
        arguments.model,
        arguments.capability,
        arguments.output,
    )
    print(manifest["build_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
