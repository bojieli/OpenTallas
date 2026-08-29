#!/usr/bin/env python3
"""Materialise the pinned Qwen3-8B acceptance workloads.

Writes one canonical JSON per workload plus an index, so that every backend,
the cycle model and the independent oracle consume byte-identical prompts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.workloads.qwen3 import build_workloads  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--output", type=Path, default=REPO / "build" / "workloads" / "qwen3-8b"
    )
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(args.snapshot), local_files_only=True, trust_remote_code=False
    )
    tokenizer_sha = hashlib.sha256(
        (args.snapshot / "tokenizer.json").read_bytes()
    ).hexdigest()

    workloads = build_workloads(tokenizer, max_new_tokens=args.max_new_tokens)
    args.output.mkdir(parents=True, exist_ok=True)
    index = {
        "schema": "opentallas.abi3.workload_index.v1",
        "model_id": "qwen3-8b",
        "snapshot": str(args.snapshot),
        "tokenizer_sha256": tokenizer_sha,
        "workloads": {},
    }
    for wid, workload in sorted(workloads.items()):
        body = workload.to_dict()
        path = args.output / f"{wid}.json"
        path.write_bytes(canonical_json(body))
        index["workloads"][wid] = {
            "path": path.name,
            "kind": workload.kind,
            "digest": workload.digest,
            "prompt_token_count": len(workload.token_ids),
            "max_new_tokens": workload.max_new_tokens,
        }
        print(
            f"{wid:18s} kind={workload.kind:16s} "
            f"tokens={len(workload.token_ids):6d} digest={workload.digest[:16]}"
        )
    (args.output / "index.json").write_bytes(canonical_json(index))
    print(f"\nwrote {len(workloads)} workloads to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
