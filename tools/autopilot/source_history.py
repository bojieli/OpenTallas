#!/usr/bin/env python3
"""Package the historical Git inputs recipes actually read, before staging a source.

The pack contains immutable commits, path trees and selected blobs, not their entire
ancestor histories. Installing it adds objects only: no refs, index, RTL or constraints
change. Missing pins are reported without substituting today's RTL or adding a gate.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile


def git(repo, *args, data=None):
    return subprocess.run(["git", "-C", str(repo), *args], input=data,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def probe(repo, specs):
    """Resolve a batch, including missing historical commits, without shell expansion."""
    specs = list(dict.fromkeys(specs))
    if not specs:
        return {}
    if any("\n" in s or "\r" in s for s in specs):
        raise ValueError("Git input names must not contain newlines")
    lines = git(repo, "cat-file", "--batch-check=%(objectname) %(objecttype)",
                data=("\n".join(specs) + "\n").encode()).decode().splitlines()
    return {s: (line.split()[0] if line.rsplit(" ", 1)[-1] in ("commit", "tree", "blob") else None)
            for s, line in zip(specs, lines)}


def read_blobs(repo, specs):
    specs = list(specs)
    if not specs:
        return []
    body = io.BytesIO(git(repo, "cat-file", "--batch", data=("\n".join(specs) + "\n").encode()))
    result = []
    for _ in specs:
        header = body.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError("recipe is not an available Git blob: " + b" ".join(header).decode())
        result.append(body.read(int(header[2])))
        if body.read(1) != b"\n":
            raise ValueError("invalid Git batch response")
    return result


def recipe_records(source, revision=None):
    source = Path(source)
    if revision:
        paths = git(source, "ls-tree", "-r", "--name-only", "-z", revision,
                    "--", "physical/die_plan").decode().split("\0")
        paths = sorted(p for p in paths if p.endswith(".json") and "recipe" in Path(p).name)
        blobs = read_blobs(source, (revision + ":" + p for p in paths))
    else:
        paths = sorted((source / "physical/die_plan").rglob("*recipe*.json"))
        blobs = [p.read_bytes() for p in paths]

    records = []
    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get("files"), list):
                records.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for blob in blobs:
        try:
            visit(json.loads(blob))
        except (ValueError, UnicodeDecodeError):
            continue
    return records


def collect_pins(source, revision=None):
    """Match gen_core_kit_hbm.fetch: files_at wins, then forced pin, then missing-tree fallback."""
    records = recipe_records(source, revision)
    fallback = {f for rec in records for f in rec["files"] if isinstance(f, str)
                and rec.get("source_commit") and not rec.get("read_at_commit")
                and f not in (rec.get("files_at") or {})}
    present = probe(source, (revision + ":" + f for f in fallback)) if revision else {}
    pins = {}
    for rec in records:
        for name in rec["files"]:
            if not isinstance(name, str):
                continue
            overrides = rec.get("files_at") or {}
            if name in overrides:
                pin = overrides[name]
            elif rec.get("read_at_commit"):
                pin = rec.get("source_commit", "HEAD")
            else:
                exists = present.get(revision + ":" + name) if revision else (Path(source) / name).is_file()
                pin = rec.get("source_commit") if not exists else None
            if pin and pin != "HEAD":
                pins.setdefault(pin, set()).add(name)
    return {pin: sorted(names) for pin, names in sorted(pins.items())}


def pack_history(source, authority, output, revision=None):
    pins = collect_pins(source, revision)
    specs = []
    for pin, names in pins.items():
        specs.extend((pin + "^{commit}", pin + "^{tree}"))
        for name in names:
            specs.extend(pin + ":" + "/".join(name.split("/")[:n])
                         for n in range(1, len(name.split("/")) + 1))
    resolved = probe(authority, specs)
    objects, missing = set(), []
    for pin, names in pins.items():
        commit, tree = resolved.get(pin + "^{commit}"), resolved.get(pin + "^{tree}")
        if not commit or not tree:
            missing.append({"pin": pin, "reason": "historical commit unavailable"})
            continue
        objects.update((commit, tree))
        for name in names:
            for n in range(1, len(name.split("/")) + 1):
                spec = pin + ":" + "/".join(name.split("/")[:n])
                if not resolved.get(spec):
                    missing.append({"pin": pin, "path": name, "reason": "historical path unavailable"})
                    break
                objects.add(resolved[spec])
    identity = hashlib.sha256(json.dumps([pins, sorted(objects), missing], sort_keys=True).encode()).hexdigest()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    pack = output / ("source-history-" + identity[:16] + ".pack") if objects else None
    if pack and not pack.exists():
        with tempfile.NamedTemporaryFile(dir=output, delete=False) as stream:
            tmp = Path(stream.name)
            try:
                subprocess.run(["git", "-C", str(authority), "pack-objects", "--stdout"],
                               input=("\n".join(sorted(objects)) + "\n").encode(), stdout=stream, check=True)
                stream.flush()
                os.replace(tmp, pack)
            finally:
                tmp.unlink(missing_ok=True)
    report = {"pins": len(pins), "objects": len(objects), "missing": missing,
              "pack": str(pack) if pack else None, "bytes": pack.stat().st_size if pack else 0,
              "identity": identity}
    receipt = output / ("source-history-" + identity[:16] + ".json")
    if not receipt.exists():
        receipt.write_text(json.dumps(report, indent=2) + "\n")
    return report


def install_pack(repo, pack):
    with Path(pack).open("rb") as stream:
        return subprocess.run(["git", "-C", str(repo), "index-pack", "--stdin"], stdin=stream,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.decode().strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack")
    pack.add_argument("--source", required=True)
    pack.add_argument("--authority", required=True)
    pack.add_argument("--revision")
    pack.add_argument("--out", required=True)
    install = commands.add_parser("install")
    install.add_argument("--repo", required=True)
    install.add_argument("--pack", required=True)
    args = parser.parse_args(argv)
    if args.command == "pack":
        print(json.dumps(pack_history(args.source, args.authority, args.out, args.revision)))
    else:
        print(install_pack(args.repo, args.pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
