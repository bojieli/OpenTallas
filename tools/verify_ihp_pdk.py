#!/usr/bin/env python3
"""Verify a pristine pinned IHP Open PDK checkout semantically.

The manifest covers every tracked regular file and symlink in the superproject
and initialized submodules.  Gitlink commits are separate records.  Git's
administrative files are deliberately excluded so clone depth and object-pack
layout cannot change the identity.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs" / "pdk" / "ihp_sg13g2_physical_lock.json"


class VerificationError(RuntimeError):
    """The checkout is absent, dirty, incomplete, or differs from the lock."""


def git_bytes(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if completed.returncode != 0:
        diagnostic = completed.stderr.decode("utf-8", errors="replace")
        raise VerificationError(
            f"git {' '.join(arguments)} failed in {repository}: {diagnostic.strip()}"
        )
    return completed.stdout


def git_text(repository: Path, *arguments: str) -> str:
    return git_bytes(repository, *arguments).decode("utf-8").strip()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def indexed_entries(repository: Path) -> list[tuple[str, str, str]]:
    raw = git_bytes(repository, "ls-files", "-s", "-z")
    entries: list[tuple[str, str, str]] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, object_id, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise VerificationError(
                f"unmerged index entry in {repository}: {raw_path!r}"
            )
        try:
            relative = raw_path.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise VerificationError(
                f"tracked path is not UTF-8 in {repository}: {raw_path!r}"
            ) from exc
        entries.append((mode, object_id, relative))
    return entries


def semantic_tree_identity(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    if not (root / ".git").exists():
        raise VerificationError(f"not an IHP Git checkout: {root}")

    records: list[bytes] = []
    submodules: dict[str, str] = {}
    counts: Counter[str] = Counter()
    payload_bytes = 0

    def visit(repository: Path, prefix: str) -> None:
        nonlocal payload_bytes
        dirty = git_bytes(
            repository,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        )
        if dirty:
            rendered = dirty.replace(b"\0", b"\n").decode(
                "utf-8", errors="replace"
            )
            raise VerificationError(f"checkout is not pristine at {repository}:\n{rendered}")

        for mode, object_id, relative in indexed_entries(repository):
            logical = f"{prefix}{relative}"
            path = repository / relative
            if mode in {"100644", "100755"}:
                if path.is_symlink() or not path.is_file():
                    raise VerificationError(
                        f"tracked regular file has wrong filesystem type: {logical}"
                    )
                payload = path.read_bytes()
                digest = sha256_bytes(payload)
                size = len(payload)
                payload_bytes += size
                counts["regular_files"] += 1
                records.append(
                    f"{logical}\0file\0{mode}\0{size}\0{digest}\n".encode("utf-8")
                )
            elif mode == "120000":
                if not path.is_symlink():
                    raise VerificationError(f"tracked symlink is not a symlink: {logical}")
                target = os.readlink(path)
                payload = target.encode("utf-8")
                digest = sha256_bytes(payload)
                size = len(payload)
                payload_bytes += size
                counts["symlinks"] += 1
                records.append(
                    f"{logical}\0symlink\0{mode}\0{size}\0{digest}\0{target}\n".encode(
                        "utf-8"
                    )
                )
            elif mode == "160000":
                if not path.is_dir() or not (path / ".git").exists():
                    raise VerificationError(f"submodule is not initialized: {logical}")
                observed_commit = git_text(path, "rev-parse", "HEAD")
                if observed_commit != object_id:
                    raise VerificationError(
                        f"submodule commit mismatch at {logical}: "
                        f"index={object_id}, checkout={observed_commit}"
                    )
                counts["gitlinks"] += 1
                submodules[logical] = observed_commit
                records.append(
                    f"{logical}\0gitlink\0{mode}\0{observed_commit}\n".encode("utf-8")
                )
                visit(path, f"{logical}/")
            else:
                raise VerificationError(f"unsupported Git mode {mode} at {logical}")

    visit(root, "")
    ordered = sorted(records)
    manifest = sha256_bytes(b"".join(ordered))
    counts["payload_entries"] = counts["regular_files"] + counts["symlinks"]
    counts["semantic_records"] = len(ordered)
    return {
        "root_commit": git_text(root, "rev-parse", "HEAD"),
        "submodules": dict(sorted(submodules.items())),
        "tree": {
            **dict(sorted(counts.items())),
            "payload_bytes": payload_bytes,
            "manifest_sha256": manifest,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdk_root", type=Path, help="IHP Open PDK Git checkout")
    parser.add_argument(
        "--observe",
        action="store_true",
        help="print the semantic identity without comparing it with the repository lock",
    )
    args = parser.parse_args()

    try:
        observed = semantic_tree_identity(args.pdk_root)
        if args.observe:
            print(json.dumps({"status": "observed", **observed}, indent=2))
            return 0

        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        expected = {
            "root_commit": lock["pdk"]["commit"],
            "submodules": lock["pdk"]["submodules"],
            "tree": {
                key: lock["pdk"]["installed_tree"][key]
                for key in observed["tree"]
            },
        }
        if observed != expected:
            print(json.dumps({"expected": expected, "observed": observed}, indent=2))
            return 1
        print(
            json.dumps(
                {
                    "status": "pass",
                    "root": str(args.pdk_root.resolve()),
                    **observed,
                },
                indent=2,
            )
        )
        return 0
    except (OSError, VerificationError, KeyError, json.JSONDecodeError) as exc:
        print(f"IHP PDK verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
