#!/usr/bin/env python3
"""Create-once build of the authenticated Qwen exact-8K batch campaign.

Only the pinned tokenizer and official chat template are loaded.  No language
model is imported or executed, and every oracle binding is emitted as pending.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from compiler.workloads.qwen3_heterogeneous_8k import (  # noqa: E402
    DEFAULT_CHECKPOINT_LOCK,
    DEFAULT_EXACT_8K_CONSTRUCTION,
    DEFAULT_SHARED_SEMANTICS,
    DEFAULT_SNAPSHOT,
    DEFAULT_TERMINALBENCH_SUITE,
    QwenHeterogeneousCampaignError,
    authenticate_campaign_inputs,
    build_campaign_documents,
    validate_workload_set,
)


DEFAULT_OUTPUT = REPO / "build/workloads/qwen3-heterogeneous-exact-8k-v1"


def build_to_directory(
    output: Path,
    *,
    snapshot: Path = DEFAULT_SNAPSHOT,
    checkpoint_lock: Path = DEFAULT_CHECKPOINT_LOCK,
    shared_semantics: Path = DEFAULT_SHARED_SEMANTICS,
    terminalbench_suite: Path = DEFAULT_TERMINALBENCH_SUITE,
    exact_8k_construction: Path = DEFAULT_EXACT_8K_CONSTRUCTION,
) -> dict:
    """Authenticate, validate, and atomically publish a new campaign directory."""

    destination = Path(output).resolve()
    if destination.exists():
        raise QwenHeterogeneousCampaignError(
            f"refusing to replace existing create-once campaign: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    inputs = authenticate_campaign_inputs(
        snapshot=snapshot,
        checkpoint_lock_path=checkpoint_lock,
        shared_semantics_path=shared_semantics,
        terminalbench_suite_path=terminalbench_suite,
        construction_path=exact_8k_construction,
    )
    documents, manifest = build_campaign_documents(inputs, repo=REPO)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent)
    )
    try:
        for relative, payload in sorted(documents.items()):
            path = temporary / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        expected_workloads = {
            lane["workload"]["workload_id"]: load_strict_json(
                temporary / lane["workload"]["file"]["path"]
            )
            for lane in manifest["lanes"]
        }
        validate_workload_set(
            temporary / "manifest.json",
            codec=inputs.chat,
            repo=REPO,
            expected_workloads=expected_workloads,
            expected_sources=manifest["sources"],
        )
        os.rename(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--checkpoint-lock", type=Path, default=DEFAULT_CHECKPOINT_LOCK
    )
    parser.add_argument(
        "--shared-semantics", type=Path, default=DEFAULT_SHARED_SEMANTICS
    )
    parser.add_argument(
        "--terminalbench-suite", type=Path, default=DEFAULT_TERMINALBENCH_SUITE
    )
    parser.add_argument(
        "--exact-8k-construction",
        type=Path,
        default=DEFAULT_EXACT_8K_CONSTRUCTION,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        manifest = build_to_directory(
            args.output,
            snapshot=args.snapshot,
            checkpoint_lock=args.checkpoint_lock,
            shared_semantics=args.shared_semantics,
            terminalbench_suite=args.terminalbench_suite,
            exact_8k_construction=args.exact_8k_construction,
        )
    except (OSError, ValueError) as exc:
        print(f"campaign build refused: {exc}", file=sys.stderr)
        return 2
    print(
        f"created {args.output} with workload_set_id="
        f"{manifest['workload_set_id']}"
    )
    for lane in manifest["lanes"]:
        print(
            f"lane={lane['lane_index']} category={lane['category']} "
            f"workload={lane['workload']['workload_id']} tokens=8000 "
            "max_new=256 oracle=pending"
        )
    print("claim boundary: tokenizer-only preparation; no model tokens or TPOT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
