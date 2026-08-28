"""OpenTallas compiler command line."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from compiler.build import BuildError, build_deployment
from compiler.checking.inverse import InverseCheckError
from compiler.image.rom import RomImageError
from compiler.ir.model import IRValidationError
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
    return result


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
    except (
        BuildError,
        IRValidationError,
        RomImageError,
        MicrocodeError,
        InverseCheckError,
        OSError,
    ) as exc:
        print(f"compiler error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("argparse accepted an unknown command")
