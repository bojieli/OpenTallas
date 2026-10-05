#!/usr/bin/env python3
"""Bind every declared checkpoint byte into a ``checkpoint.lock.json``.

``compiler/frontend/checkpoint.py::build_checkpoint_lock`` is the authority and
this tool only gives it a command line.  It reads the immutable
``checkpoint_source.json`` expectation, reads every file the expectation
declares, and refuses the build when a digest, a size, the safetensors index
coverage, or the payload total differs.  Each shard's header is parsed and every
tensor's payload is hashed, so the lock carries the per-tensor digest that a
kernel-IR ``CheckpointBinding`` later quotes: a tensor cannot be substituted
between the lock and a deployment without the mismatch surfacing.

The lock is host state, not a release artifact -- it names a snapshot directory
on this machine -- so it belongs under the cache root rather than in the
repository, which is where the front ends look for it:

    PYTHONPATH=. python3 tools/build_checkpoint_lock.py \\
      --source compiler/models/deepseek-v4-pro-0813/checkpoint_source.json \\
      --snapshot ~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Pro-0813/snapshots/72e1d3230f6c080a530b0a1d46f8eb4602340597 \\
      --output ~/.cache/opentallas/deepseek-v4-pro-0813/checkpoint.lock.json

Every byte of the checkpoint is read once, so the wall time is a full pass over
the payload: about 25 minutes for DeepSeek-V4-Flash-0731's 156 GB and about two
and a half hours for DeepSeek-V4-Pro-0813's 893 GB on a host reading at 100 MB/s.
Two runs over the same snapshot produce the same ``lock_id``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.checkpoint import (  # noqa: E402
    CheckpointError,
    build_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="the model's immutable checkpoint_source.json",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        required=True,
        help="the local snapshot directory holding the declared files",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing lock"
    )
    args = parser.parse_args(argv)

    output = args.output.expanduser()
    if output.exists() and not args.force:
        print(f"{output} exists; pass --force to overwrite", file=sys.stderr)
        return 4
    try:
        source = json.loads(args.source.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read checkpoint source: {exc}", file=sys.stderr)
        return 2
    started = time.monotonic()
    try:
        lock = build_checkpoint_lock(args.snapshot.expanduser(), source)
    except CheckpointError as exc:
        print(f"checkpoint lock refused: {exc}", file=sys.stderr)
        return 3
    elapsed = time.monotonic() - started
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(lock) + b"\n")
    checkpoint = lock["checkpoint"]
    print(f"wrote {output}")
    print(f"  lock_id            {lock['lock_id']}")
    print(f"  shards             {checkpoint['shard_count']}")
    print(f"  tensors            {checkpoint['tensor_count']}")
    print(f"  payload bytes      {checkpoint['payload_bytes']}")
    print(f"  tensor content     {checkpoint['tensor_content_sha256']}")
    print(f"  read and hashed in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
