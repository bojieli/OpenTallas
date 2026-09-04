#!/usr/bin/env python3
"""Append human-written notes to a physical record without touching its data.

``run_abi3_physical.py`` writes every field of a record itself and has no
free-text option, so findings that belong next to the numbers (what the
critical path runs through, which assumption a cell count contradicts) are
added afterwards with this script.  The record's tool-written content is
hashed before the first annotation and the hash is stored beside the notes,
so a reader can strip ``notes`` and ``annotation`` and confirm nothing else
changed: ``--verify`` does exactly that.

    tools/annotate_physical_record.py RECORD --note TEXT [--note TEXT ...]
    tools/annotate_physical_record.py RECORD --verify
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ANNOTATION_KEYS = ("notes", "annotation")


def tool_record_sha256(record: dict) -> str:
    """Hash the record with the annotation keys removed, in canonical JSON."""
    stripped = {k: v for k, v in record.items() if k not in ANNOTATION_KEYS}
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def annotate(path: Path, notes: list[str]) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    digest = tool_record_sha256(record)
    annotation = record.get("annotation")
    if annotation is None:
        annotation = {
            "tool_record_sha256": digest,
            "basis": (
                "sha256 of the record as written by the flow tool, canonical "
                "JSON with the notes and annotation keys removed; recompute "
                "with tools/annotate_physical_record.py --verify"
            ),
        }
    elif annotation.get("tool_record_sha256") != digest:
        raise SystemExit(
            f"{path}: tool-written content changed since the first annotation "
            f"({annotation.get('tool_record_sha256')} -> {digest}); refusing"
        )
    annotation["annotated_at"] = (
        _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    )
    annotation["annotated_by"] = "tools/annotate_physical_record.py"
    record.setdefault("notes", []).extend(notes)
    record["annotation"] = annotation
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def verify(path: Path) -> bool:
    record = json.loads(path.read_text(encoding="utf-8"))
    annotation = record.get("annotation")
    if annotation is None:
        print(f"{path}: not annotated")
        return "notes" not in record
    ok = annotation.get("tool_record_sha256") == tool_record_sha256(record)
    print(f"{path}: {'intact' if ok else 'TOOL-WRITTEN CONTENT CHANGED'} "
          f"({len(record.get('notes', []))} notes)")
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("record", type=Path)
    parser.add_argument("--note", action="append", default=[], help="note to append (repeatable)")
    parser.add_argument("--verify", action="store_true", help="check the tool-written content hash")
    args = parser.parse_args(argv)
    if args.verify:
        return 0 if verify(args.record) else 1
    if not args.note:
        parser.error("give at least one --note, or --verify")
    annotate(args.record, args.note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
