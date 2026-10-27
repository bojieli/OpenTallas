#!/usr/bin/env python3
"""Apply source replacements to every private Verilator hierarchy argument file.

The top can inline instances of modules that also have hierarchical libraries.
Updating library arguments alone creates a mixed design, so include top args.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shlex


def overlay(args_files, sources):
    sources = {Path(s).name: Path(s).resolve(strict=True) for s in sources}
    changes = []
    for args in args_files:
        args = Path(args)
        if args.is_symlink():
            raise ValueError(f"refuse shared argument symlink: {args}")
        lines = args.read_text().splitlines()
        for i, line in enumerate(lines):
            tokens = shlex.split(line)
            if len(tokens) != 1:
                continue
            old = Path(tokens[0]); new = sources.get(old.name)
            if new is None or old == new:
                continue
            changes.append({"args": str(args), "old": str(old), "new": str(new),
                            "sha256": hashlib.sha256(new.read_bytes()).hexdigest()})
            lines[i] = shlex.quote(str(new))
        args.write_text("\n".join(lines) + "\n")
    return changes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("obj", type=Path)
    ap.add_argument("--source", action="append", required=True, type=Path)
    ap.add_argument("--receipt", type=Path, required=True)
    ns = ap.parse_args()
    files = sorted(ns.obj.glob("*__hierMkArgs.f"))
    if not files:
        ap.error("no hierarchy argument files")
    changes = overlay(files, ns.source)
    ns.receipt.write_text(json.dumps({"argument_files": len(files), "changes": changes}, indent=2) + "\n")
    print(f"OVERLAY {len(changes)} sources across {len(files)} argument files")


if __name__ == "__main__": main()
