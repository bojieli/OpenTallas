#!/usr/bin/env python3
"""Verify the selected Ciel SKY130A payload against its repository lock."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs" / "pdk" / "sky130_physical_lock.json"


def tree_identity(root: Path) -> tuple[int, int, str]:
    resolved = root.resolve(strict=True)
    files = sorted(path for path in resolved.rglob("*") if path.is_file())
    records: list[str] = []
    total_bytes = 0
    for path in files:
        payload = path.read_bytes()
        size = len(payload)
        total_bytes += size
        digest = hashlib.sha256(payload).hexdigest()
        relative = path.relative_to(resolved).as_posix()
        records.append(f"{relative}\0{size}\0{digest}\n")
    manifest = hashlib.sha256("".join(records).encode("utf-8")).hexdigest()
    return len(files), total_bytes, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdk_root", type=Path, help="enabled SKY130A variant root")
    args = parser.parse_args()

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = lock["pdk"]["installed_tree"]
    sources = args.pdk_root.resolve(strict=True) / "SOURCES"
    if sources.read_text(encoding="utf-8").strip() != (
        f"open_pdks {lock['pdk']['open_pdks_commit']}"
    ):
        raise SystemExit(f"unexpected PDK SOURCES identity: {sources}")

    count, size, digest = tree_identity(args.pdk_root)
    observed = {"files": count, "bytes": size, "manifest_sha256": digest}
    required = {key: expected[key] for key in observed}
    if observed != required:
        print(json.dumps({"expected": required, "observed": observed}, indent=2))
        return 1
    print(json.dumps({"status": "pass", "root": str(args.pdk_root), **observed}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
