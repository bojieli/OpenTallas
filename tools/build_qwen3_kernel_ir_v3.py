#!/usr/bin/env python3
"""Export the pinned Qwen3-8B checkpoint into Tensor Kernel IR v3 JSON.

The document this writes is the single backend-neutral input to both the shared
HBM/SRAM backend and the ROM backend.  Two runs on the same checkpoint produce
byte-identical output and the same ``graph_id``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.frontends.v3.qwen3 import (  # noqa: E402
    DEFAULT_CHECKPOINT_LOCK,
    DEFAULT_SNAPSHOT,
    MAX_CONTEXT_TOKENS,
    Qwen3KernelIRError,
    export_qwen3_kernel_graph,
    verify_checkpoint_bindings,
)
from compiler.ir.v3.kernel_ir import check_neutral  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402


def _sample_names(graph, lock_path: Path, mode: str) -> list[str] | None:
    weights = [t.tensor_id for t in graph.tensors if t.role == "weight"]
    if mode == "none":
        return []
    if mode == "all":
        return None
    if mode == "sample":
        return sorted(weights)[:: max(1, len(weights) // 16)]
    lock = json.loads(lock_path.read_text())
    shard = min(lock["shards"], key=lambda item: item["file_size_bytes"])
    return sorted(record["name"] for record in shard["tensors"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--checkpoint-lock", type=Path, default=DEFAULT_CHECKPOINT_LOCK)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "compiler/models/qwen3-8b/config.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/ir-v3/qwen3-8b/kernel_ir.v3.json"
    )
    parser.add_argument("--maximum-new-tokens", type=int, default=MAX_CONTEXT_TOKENS)
    parser.add_argument(
        "--build-lock",
        action="store_true",
        help="build the checkpoint lock from the snapshot when it is missing",
    )
    parser.add_argument(
        "--verify-bindings",
        choices=("none", "sample", "smallest-shard", "all"),
        default="sample",
        help="how much of the weight image to read back and hash",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="require the existing output to already equal this export",
    )
    arguments = parser.parse_args()

    try:
        graph = export_qwen3_kernel_graph(
            snapshot=arguments.snapshot,
            checkpoint_lock_path=arguments.checkpoint_lock,
            config_path=arguments.config,
            maximum_new_tokens=arguments.maximum_new_tokens,
            build_lock_if_missing=arguments.build_lock,
        )
    except Qwen3KernelIRError as exc:
        print(f"qwen3 kernel IR v3 export failed: {exc}", file=sys.stderr)
        return 1

    errors = check_neutral(graph)
    if errors:
        for error in errors:
            print(f"neutrality: {error}", file=sys.stderr)
        return 1

    names = _sample_names(
        graph, Path(arguments.checkpoint_lock), arguments.verify_bindings
    )
    verification = {"checked_bytes": 0, "checked_tensors": 0, "shards": []}
    if names is None or names:
        try:
            verification = verify_checkpoint_bindings(
                graph,
                snapshot=arguments.snapshot,
                checkpoint_lock_path=arguments.checkpoint_lock,
                tensor_names=names,
            )
        except Qwen3KernelIRError as exc:
            print(f"checkpoint binding verification failed: {exc}", file=sys.stderr)
            return 1

    body = graph.to_dict()
    body["graph_id"] = graph.graph_id
    payload = canonical_json(body)
    output = Path(arguments.output)
    if arguments.check:
        if not output.is_file() or output.read_bytes() != payload:
            print(f"{output} differs from this export", file=sys.stderr)
            return 1
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_name(f".{output.name}.tmp")
        with staging.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging, output)

    print(f"graph_id       {graph.graph_id}")
    print(f"model_id       {graph.model_id}")
    print(f"kernels        {len(graph.kernels)}")
    print(f"tensors        {len(graph.tensors)}")
    print(f"states         {len(graph.states)}")
    print(f"eos_token_ids  {graph.generation_policy['eos_token_ids']}")
    print(
        "bindings       "
        f"{verification['checked_tensors']} verified, "
        f"{verification['checked_bytes']} bytes, shards {verification['shards']}"
    )
    print(f"bytes          {len(payload)}")
    print(f"path           {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
