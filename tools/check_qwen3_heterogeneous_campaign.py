#!/usr/bin/env python3
"""Validate Qwen exact-8K workload and independent-reference set contracts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    publish_bytes_atomic_no_replace,
)
from compiler.workloads.qwen3_heterogeneous_8k import (  # noqa: E402
    DEFAULT_CHECKPOINT_LOCK,
    DEFAULT_EXACT_8K_CONSTRUCTION,
    DEFAULT_SHARED_SEMANTICS,
    DEFAULT_SNAPSHOT,
    DEFAULT_TERMINALBENCH_SUITE,
    authenticate_campaign_inputs,
    build_reference_set,
    build_workloads,
    validate_reference_set,
    validate_workload_set,
)


DEFAULT_MANIFEST = (
    REPO
    / "configs/abi3/workloads/qwen3_heterogeneous_exact_8k_v1/manifest.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
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
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--reference-set",
        type=Path,
        help="validate an already frozen eight-oracle reference set",
    )
    group.add_argument(
        "--freeze-reference-set",
        type=Path,
        help=(
            "create-once freeze all eight expected oracle files; refuses if any "
            "file or production authentication is missing"
        ),
    )
    parser.add_argument(
        "--require-production-ready",
        action="store_true",
        help="return a failure status when no complete reference set was supplied",
    )
    args = parser.parse_args()
    try:
        inputs = authenticate_campaign_inputs(
            snapshot=args.snapshot,
            checkpoint_lock_path=args.checkpoint_lock,
            shared_semantics_path=args.shared_semantics,
            terminalbench_suite_path=args.terminalbench_suite,
            construction_path=args.exact_8k_construction,
        )
        expected = build_workloads(inputs)
        campaign = validate_workload_set(
            args.manifest,
            codec=inputs.chat,
            repo=REPO,
            expected_workloads=expected,
            expected_sources={
                key: value for key, value in campaign_sources(inputs).items()
            },
        )
        if args.freeze_reference_set is not None:
            body = build_reference_set(campaign, codec=inputs.chat)
            publish_bytes_atomic_no_replace(
                args.freeze_reference_set, canonical_json_bytes(body)
            )
            print(
                f"production reference set frozen: {body['reference_set_id']}"
            )
            return 0
        if args.reference_set is not None:
            body = validate_reference_set(
                args.reference_set, campaign=campaign, codec=inputs.chat
            )
            print(
                f"production reference set valid: {body['reference_set_id']}"
            )
            return 0
    except FileExistsError as exc:
        print(f"campaign validation refused: create-once output exists: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"campaign validation refused: {exc}", file=sys.stderr)
        return 2
    print(
        "workload set valid: tokenizer-authenticated exact-8K preparation; "
        "8/8 independent production oracles remain pending"
    )
    print("no runnable heterogeneous batch request or Gate-1/TPOT claim was emitted")
    return 2 if args.require_production_ready else 0


def campaign_sources(inputs):
    """Build the source block exactly as the content-addressed builder does."""

    # Keep the public CLI thin while avoiding a second, subtly different source
    # authenticator.  build_campaign_documents is deterministic and model-free.
    from compiler.workloads.qwen3_heterogeneous_8k import build_campaign_documents

    _documents, manifest = build_campaign_documents(inputs, repo=REPO)
    return manifest["sources"]


if __name__ == "__main__":
    raise SystemExit(main())
