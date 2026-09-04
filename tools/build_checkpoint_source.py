#!/usr/bin/env python3
"""Derive a model's immutable ``checkpoint_source.json`` from its snapshot.

A checkpoint source is the *expectation* half of the two-sided identity the
compiler front ends rely on: ``compiler/frontend/checkpoint.py`` builds the lock
by reading every declared byte and refuses any file whose digest or size differs
from the expectation recorded here.  Writing the expectation from the same bytes
the lock will read would make that check circular, so this tool computes the
digests locally *and* confronts them with an independent witness -- the model
registry's own per-file record at the pinned revision, which is published before
any byte reaches this host.  A file whose local digest differs from the registry
is reported and the tool fails closed; a file the registry records without a
content digest (registries omit them for small non-LFS files) is reported as
witnessed by size alone.

The registry listing is supplied as JSON rather than fetched, so a build is
reproducible without network access and the witness is itself an artifact:

    curl -s "https://huggingface.co/api/models/<repo>?blobs=true" > listing.json
    PYTHONPATH=. python3 tools/build_checkpoint_source.py \\
      --repository deepseek-ai/DeepSeek-V4-Pro-0813 \\
      --revision 72e1d3230f6c080a530b0a1d46f8eb4602340597 \\
      --snapshot ~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4-Pro-0813/snapshots/72e1d3230f6c080a530b0a1d46f8eb4602340597 \\
      --registry-listing listing.json \\
      --output compiler/models/deepseek-v4-pro-0813/checkpoint_source.json

Two runs over the same snapshot produce byte-identical output.  The tool never
writes the checkpoint lock: ``build_checkpoint_lock`` does that, and it re-reads
and re-verifies every byte against the file this tool wrote.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.checkpoint import (  # noqa: E402
    CheckpointError,
    validate_checkpoint_source,
)
from compiler.ir.model import canonical_json_bytes  # noqa: E402

CHUNK_BYTES = 8 * 1024 * 1024
SHARD_SUFFIX = ".safetensors"


class CheckpointSourceError(RuntimeError):
    """Raised when a snapshot and its registry witness disagree."""


def _sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _snapshot_files(snapshot: Path) -> list[str]:
    """Every regular file in the snapshot, as forward-slash relative paths."""

    found: list[str] = []
    for path in sorted(snapshot.rglob("*")):
        if path.is_dir():
            continue
        if not path.is_file():
            raise CheckpointSourceError(
                f"snapshot entry is not a regular file: {path}"
            )
        found.append(path.relative_to(snapshot).as_posix())
    if not found:
        raise CheckpointSourceError(f"snapshot holds no files: {snapshot}")
    return found


def _model_files(snapshot: Path, witness: dict[str, dict[str, Any]]) -> list[str]:
    """The registry's file set at this revision, required to be present locally.

    The registry defines what the checkpoint *is*; a local snapshot directory is
    a working copy that legitimately accumulates other things -- interpreter
    caches, and in this repository a published deployment written beside the
    weights.  Those are not part of the checkpoint identity and are reported
    rather than bound.  Every file the registry does list must be present, and
    its bytes are then confronted with the registry's own record.
    """

    present = set(_snapshot_files(snapshot))
    missing = sorted(witness.keys() - present)
    if missing:
        raise CheckpointSourceError(
            f"snapshot is missing {len(missing)} file(s) the registry lists at "
            f"this revision: {missing[:6]}"
        )
    return sorted(witness)


def _registry_witness(listing: Any, revision: str) -> dict[str, dict[str, Any]]:
    """The registry's per-file record, keyed by repository-relative path."""

    if not isinstance(listing, dict):
        raise CheckpointSourceError("registry listing must be a JSON object")
    observed_revision = listing.get("sha")
    if observed_revision != revision:
        raise CheckpointSourceError(
            f"registry listing is for revision {observed_revision!r}, not the "
            f"pinned {revision!r}"
        )
    siblings = listing.get("siblings")
    if not isinstance(siblings, list) or not siblings:
        raise CheckpointSourceError(
            "registry listing has no siblings; fetch it with ?blobs=true so "
            "sizes and content digests are present"
        )
    witness: dict[str, dict[str, Any]] = {}
    for entry in siblings:
        if not isinstance(entry, dict):
            raise CheckpointSourceError("registry sibling must be an object")
        name = entry.get("rfilename")
        if not isinstance(name, str) or not name:
            raise CheckpointSourceError("registry sibling has no rfilename")
        if name in witness:
            raise CheckpointSourceError(f"registry lists {name!r} twice")
        lfs = entry.get("lfs")
        digest = None
        if isinstance(lfs, dict):
            raw = lfs.get("sha256")
            if isinstance(raw, str) and len(raw) == 64:
                digest = raw
        witness[name] = {"sha256": digest, "size_bytes": entry.get("size")}
    return witness


def _confront(
    observed: list[dict[str, Any]], witness: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Compare local digests with the registry record, failing closed."""

    digest_witnessed: list[str] = []
    size_only: list[str] = []
    problems: list[str] = []
    for record in observed:
        path = record["path"]
        expected = witness.get(path)
        if expected is None:
            problems.append(f"{path}: absent from the registry listing")
            continue
        size = expected["size_bytes"]
        if isinstance(size, int) and size != record["size_bytes"]:
            problems.append(
                f"{path}: local size {record['size_bytes']} differs from the "
                f"registry's {size}"
            )
            continue
        if expected["sha256"] is None:
            size_only.append(path)
            continue
        if expected["sha256"] != record["sha256"]:
            problems.append(
                f"{path}: local sha256 {record['sha256']} differs from the "
                f"registry's {expected['sha256']}"
            )
            continue
        digest_witnessed.append(path)
    if problems:
        raise CheckpointSourceError(
            "snapshot and registry witness disagree:\n  "
            + "\n  ".join(problems[:12])
        )
    return {
        "digest_witnessed_file_count": len(digest_witnessed),
        "size_witnessed_file_count": len(size_only),
        "size_witnessed_files": sorted(size_only),
    }


def build_source(
    *,
    repository: str,
    revision: str,
    snapshot: Path,
    listing: Any,
    checkpoint_index: str,
    remote_code_policy: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the checkpoint source and the registry-confrontation summary."""

    snapshot = snapshot.resolve()
    if not snapshot.is_dir():
        raise CheckpointSourceError(f"snapshot is not a directory: {snapshot}")
    witness = _registry_witness(listing, revision)
    relative_paths = _model_files(snapshot, witness)
    if checkpoint_index not in relative_paths:
        raise CheckpointSourceError(
            f"the registry lists no checkpoint index {checkpoint_index!r} at "
            "this revision"
        )
    expected_files: list[dict[str, Any]] = []
    for relative in relative_paths:
        digest, size = _sha256_and_size(snapshot / relative)
        expected_files.append(
            {"path": relative, "sha256": digest, "size_bytes": size}
        )
    confrontation = _confront(expected_files, witness)
    confrontation["unlisted_local_files"] = sorted(
        set(_snapshot_files(snapshot)) - set(relative_paths)
    )
    required_files = sorted(
        relative
        for relative in relative_paths
        if relative != checkpoint_index and not relative.endswith(SHARD_SUFFIX)
    )
    shard_count = sum(
        1 for relative in relative_paths if relative.endswith(SHARD_SUFFIX)
    )
    if not shard_count:
        raise CheckpointSourceError("snapshot holds no safetensors shard")
    source = {
        "checkpoint_index": checkpoint_index,
        "expected_files": sorted(expected_files, key=lambda item: item["path"]),
        "remote_code_policy": remote_code_policy,
        "repository": repository,
        "required_files": required_files,
        "revision": revision,
        "schema": "opentallas.checkpoint_source.v1",
    }
    try:
        source = validate_checkpoint_source(source)
    except CheckpointError as exc:
        raise CheckpointSourceError(f"derived source is invalid: {exc}") from None
    confrontation["shard_count"] = shard_count
    confrontation["required_file_count"] = len(required_files)
    confrontation["expected_file_count"] = len(expected_files)
    confrontation["payload_bytes"] = sum(
        item["size_bytes"]
        for item in expected_files
        if item["path"].endswith(SHARD_SUFFIX)
    )
    return source, confrontation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument(
        "--registry-listing",
        type=Path,
        required=True,
        help="JSON from the registry's model endpoint fetched with ?blobs=true",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--checkpoint-index", default="model.safetensors.index.json"
    )
    parser.add_argument(
        "--remote-code-policy",
        default="disabled",
        choices=("disabled", "reviewed_and_pinned"),
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing output"
    )
    args = parser.parse_args(argv)

    try:
        listing = json.loads(args.registry_listing.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read registry listing: {exc}", file=sys.stderr)
        return 2
    try:
        source, confrontation = build_source(
            repository=args.repository,
            revision=args.revision,
            snapshot=args.snapshot,
            listing=listing,
            checkpoint_index=args.checkpoint_index,
            remote_code_policy=args.remote_code_policy,
        )
    except CheckpointSourceError as exc:
        print(f"checkpoint source refused: {exc}", file=sys.stderr)
        return 3
    if args.output.exists() and not args.force:
        print(f"{args.output} exists; pass --force to overwrite", file=sys.stderr)
        return 4
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(source) + b"\n")
    print(f"wrote {args.output}")
    print(
        f"  files {confrontation['expected_file_count']}"
        f" (shards {confrontation['shard_count']},"
        f" required {confrontation['required_file_count']})"
    )
    print(f"  shard payload bytes {confrontation['payload_bytes']}")
    print(
        "  registry witness: "
        f"{confrontation['digest_witnessed_file_count']} files agree on digest "
        f"and size, {confrontation['size_witnessed_file_count']} on size alone"
    )
    unlisted = confrontation["unlisted_local_files"]
    if unlisted:
        print(
            f"  {len(unlisted)} local file(s) the registry does not list at this "
            f"revision are not bound: {unlisted[:4]}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
