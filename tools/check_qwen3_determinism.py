#!/usr/bin/env python3
"""Independently compare two fresh Qwen3 deployment builds."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.ir.model import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)
from compiler.qwen3.checking import verify_deployment_artifacts  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Verify two Qwen3 builds and require identical governed bytes"
    )
    result.add_argument("--left", required=True, type=Path)
    result.add_argument("--right", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _actual_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }


def _write_new(path: Path, value: Any) -> None:
    """Write one durable report without replacing prior determinism evidence."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_json_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    left = arguments.left.resolve()
    right = arguments.right.resolve()
    if left == right:
        parser().error("--left and --right must be distinct fresh build directories")
    left_manifest = load_strict_json(left / "deployment_manifest.json")
    right_manifest = load_strict_json(right / "deployment_manifest.json")
    verify_deployment_artifacts(left, left_manifest)
    verify_deployment_artifacts(right, right_manifest)
    if left_manifest != right_manifest:
        raise RuntimeError("deployment manifests are not byte-deterministic")
    governed = {artifact["path"] for artifact in left_manifest["artifacts"]} | {
        "deployment_manifest.json"
    }
    left_files = _actual_files(left)
    right_files = _actual_files(right)
    if left_files != governed or right_files != governed:
        raise RuntimeError(
            "build directories contain missing or ungoverned files: "
            f"left={sorted(left_files ^ governed)}, right={sorted(right_files ^ governed)}"
        )
    manifest_payload = (left / "deployment_manifest.json").read_bytes()
    if manifest_payload != (right / "deployment_manifest.json").read_bytes():
        raise RuntimeError("canonical manifest bytes differ")
    body = {
        "artifact_count": len(left_manifest["artifacts"]),
        "artifact_payload_bytes": sum(
            artifact["size_bytes"] for artifact in left_manifest["artifacts"]
        ),
        "build_id": left_manifest["build_id"],
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "schema": "opentallas.qwen3.determinism_check.v1",
        "status": "pass",
    }
    report = {
        **body,
        "report_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }
    _write_new(arguments.output, report)
    print(report["report_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
