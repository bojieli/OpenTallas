#!/usr/bin/env python3
"""Build and independently check the Qwen 8,192-row acceptance profile."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import canonical_json_bytes  # noqa: E402
from compiler.tensor_accelerator.qwen_full_model_context import (  # noqa: E402
    QwenFullModelContextError,
    build_qwen_long_context_profile,
)
from compiler.tensor_accelerator.qwen_full_model_context_checking import (  # noqa: E402
    QwenFullModelContextCheckError,
    check_qwen_long_context_profile,
)


def _write_synced(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _build(base_graph: Path, output: Path) -> tuple[str, str, str]:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise QwenFullModelContextError(
            f"long-context bundle will not be overwritten: {output}"
        )
    staging = Path(
        tempfile.mkdtemp(dir=output.parent, prefix=f".{output.name}.", suffix=".tmp")
    )
    try:
        graph, profile = build_qwen_long_context_profile(Path(base_graph))
        graph_path = staging / "model_graph.v2.json"
        profile_path = staging / "context_profile.json"
        check_path = staging / "independent_check.json"
        _write_synced(graph_path, canonical_json_bytes(graph.to_dict()))
        _write_synced(profile_path, canonical_json_bytes(profile))
        check = check_qwen_long_context_profile(
            base_graph_path=Path(base_graph),
            expanded_graph_path=graph_path,
            profile_path=profile_path,
        )
        _write_synced(check_path, canonical_json_bytes(check))
        if output.exists():
            raise QwenFullModelContextError(
                f"long-context bundle will not be overwritten: {output}"
            )
        os.rename(staging, output)
        return graph.graph_id, profile["profile_id"], check["check_id"]
    finally:
        if staging.exists():
            for child in staging.iterdir():
                child.unlink()
            staging.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-graph",
        type=Path,
        default=(
            ROOT
            / "results/tensor_accelerator/qwen3_full_model_physical/"
            "source/model_graph.v2.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT
            / "results/tensor_accelerator/"
            "qwen3_long_acceptance_context_v1"
        ),
    )
    arguments = parser.parse_args()
    try:
        graph_id, profile_id, check_id = _build(
            arguments.base_graph, arguments.output
        )
    except (QwenFullModelContextError, QwenFullModelContextCheckError) as exc:
        parser.error(str(exc))
    print(f"graph_id={graph_id}")
    print(f"profile_id={profile_id}")
    print(f"independent_check_id={check_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
