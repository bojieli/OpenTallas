#!/usr/bin/env python3
"""kit_wave_edit.py: change kit_wave.json on the hub with a JSON patch and commit it in the same step (WAVE-CONFIG 11-16, FABLE-FLOW-2000 class D).

  python3 -I kit_wave_edit.py --message "KW-FIX-n: why" --patch '[{"op":"replace","path":"/dies/s81/max_inflight","value":40}]'
  python3 -I kit_wave_edit.py --message "..." --patch-file patch.json
  python3 -I kit_wave_edit.py --message "..." --set /enabled=false --set /dies/kv/owner_lane='"KV-R"'     (value = JSON; --unset /path removes)
  python3 -I kit_wave_edit.py --dry-run ...                                            (prints the diff, writes and commits nothing)

The patch is RFC 6902 (add, replace, remove, test; paths are JSON pointers, "-" appends to a list).  It is applied to the committed config
(`git show HEAD:autopilot/kit_wave.json`), never to a working copy somebody else is editing; a working copy that differs from HEAD is refused.  The
result is written in the file's format (indent 1, key order kept) and committed + pushed by ~/coord/bin/coord-commit.sh.  The wave
(kit_wave.py read_config_text) runs on the committed HEAD blob, so lanes must not edit the file in place: an uncommitted edit has no effect.
One editor at a time (.git/kit_wave_edit.lock in the coord checkout; the file names its holder)."""
import argparse
import copy
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

REL = "autopilot/kit_wave.json"


class PatchError(Exception):
    pass


def _tokens(ptr):
    if ptr == "":
        return []
    if not ptr.startswith("/"):
        raise PatchError(f"bad JSON pointer {ptr!r}")
    return [t.replace("~1", "/").replace("~0", "~") for t in ptr[1:].split("/")]


def _walk(doc, toks):
    cur = doc
    for t in toks:
        cur = _child(cur, t)
    return cur


def _child(cur, t):
    if isinstance(cur, dict):
        if t not in cur:
            raise PatchError(f"no key {t!r}")
        return cur[t]
    if isinstance(cur, list):
        try:
            return cur[int(t)]
        except (ValueError, IndexError):
            raise PatchError(f"no list index {t!r}")
    raise PatchError(f"cannot descend into {type(cur).__name__} at {t!r}")


def apply_patch(doc, ops):
    """a new document with the RFC 6902 ops applied (add, replace, remove, test); PatchError on any failed op, nothing partial"""
    doc = copy.deepcopy(doc)
    if not isinstance(ops, list):
        raise PatchError("a patch is a JSON list of operations")
    for n, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in ("add", "replace", "remove", "test") or "path" not in op:
            raise PatchError(f"op {n}: needs op (add|replace|remove|test) and path")
        kind, toks = op["op"], _tokens(op["path"])
        if kind != "remove" and "value" not in op:
            raise PatchError(f"op {n}: {kind} needs a value")
        try:
            if not toks:
                if kind == "test":
                    if doc != op["value"]:
                        raise PatchError("test failed at the root")
                    continue
                if kind == "remove":
                    raise PatchError("cannot remove the root")
                doc = copy.deepcopy(op["value"])
                continue
            parent, last = _walk(doc, toks[:-1]), toks[-1]
            if kind == "test":
                if _child(parent, last) != op["value"]:
                    raise PatchError(f"test failed at {op['path']}")
            elif isinstance(parent, dict):
                if kind in ("replace", "remove") and last not in parent:
                    raise PatchError(f"no key {last!r}")
                if kind == "remove":
                    del parent[last]
                else:
                    parent[last] = copy.deepcopy(op["value"])
            elif isinstance(parent, list):
                idx = len(parent) if last == "-" else int(last)
                if kind == "add":
                    if not 0 <= idx <= len(parent):
                        raise PatchError(f"list index {last!r} out of range")
                    parent.insert(idx, copy.deepcopy(op["value"]))
                else:
                    if not 0 <= idx < len(parent):
                        raise PatchError(f"list index {last!r} out of range")
                    if kind == "remove":
                        del parent[idx]
                    else:
                        parent[idx] = copy.deepcopy(op["value"])
            else:
                raise PatchError(f"cannot descend into {type(parent).__name__}")
        except PatchError as e:
            raise PatchError(f"op {n} ({kind} {op['path']}): {e}")
        except ValueError:
            raise PatchError(f"op {n} ({kind} {op['path']}): bad list index")
    return doc


def dump(doc):
    return json.dumps(doc, indent=1) + "\n"          # the format of the file in the hub checkout: indent 1, key order kept


def git(coord, *args, check=True):
    p = subprocess.run(["git", "-C", str(coord), *args], capture_output=True, text=True, timeout=120)
    if check and p.returncode:
        raise SystemExit(f"kit_wave_edit: git {' '.join(args)}: {p.stderr.strip() or p.stdout.strip()}")
    return p


def edit(coord, ops, message, dry=False, commit_cmd=None):
    """patch the committed config and commit it; returns the new text.  commit_cmd(message, rel) overrides coord-commit.sh (tests)"""
    coord = Path(coord)
    lock = open(coord / ".git" / "kit_wave_edit.lock", "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.seek(0)
        raise SystemExit(f"kit_wave_edit: another edit holds kit_wave_edit.lock: {lock.read().strip() or 'unknown'}")
    lock.seek(0); lock.truncate(); lock.write(f"pid={os.getpid()} cmd={' '.join(sys.argv)[:200]}\n"); lock.flush()
    head = git(coord, "show", f"HEAD:{REL}").stdout
    work_p = coord / REL
    work = work_p.read_text() if work_p.exists() else head
    if work != head:
        raise SystemExit(f"kit_wave_edit: {REL} in {coord} differs from HEAD (an uncommitted edit by someone else); "
                         f"commit or discard it first: git -C {coord} diff {REL}")
    try:
        new = dump(apply_patch(json.loads(head), ops))
    except (PatchError, ValueError) as e:
        raise SystemExit(f"kit_wave_edit: patch refused, nothing written: {e}")
    if new == head:
        print("kit_wave_edit: no change")
        return new
    if dry:
        import difflib
        sys.stdout.writelines(difflib.unified_diff(head.splitlines(True), new.splitlines(True), "HEAD:" + REL, "patched", n=1))
        return new
    tmp = work_p.with_name(work_p.name + f".edit{os.getpid()}")
    tmp.write_text(new)
    os.replace(tmp, work_p)                            # atomic: a reader never sees half a file
    try:
        if commit_cmd:
            commit_cmd(message, REL)
        else:
            subprocess.run(["bash", os.path.expanduser("~/coord/bin/coord-commit.sh"), message, REL], check=True, timeout=600)
    except Exception:
        work_p.write_text(head)                        # failed commit: put the committed text back, never leave an unpushed edit
        raise
    if git(coord, "show", f"HEAD:{REL}").stdout != new:
        work_p.write_text(git(coord, "show", f"HEAD:{REL}").stdout)
        raise SystemExit("kit_wave_edit: coord-commit did not leave the patched config at HEAD; working file restored")
    print(f"kit_wave_edit: committed {REL} at {git(coord, 'rev-parse', 'HEAD').stdout.strip()}")
    return new


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--coord", default=os.environ.get("AP_COORD", os.path.expanduser("~/coord")))
    ap.add_argument("--message", "-m", required=True, help="commit message (name the lane and why)")
    ap.add_argument("--patch", help="JSON patch (a list of ops) inline")
    ap.add_argument("--patch-file", help="JSON patch file")
    ap.add_argument("--set", action="append", default=[], metavar="/PTR=JSON", help="replace-or-add the value at the pointer")
    ap.add_argument("--unset", action="append", default=[], metavar="/PTR")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    ops = []
    try:
        if a.patch:
            ops += json.loads(a.patch)
        if a.patch_file:
            ops += json.loads(Path(a.patch_file).read_text())
        for s in a.set:
            ptr, _, val = s.partition("=")
            ops.append({"op": "add", "path": ptr, "value": json.loads(val)})     # RFC 6902 add replaces an existing member
        for u in a.unset:
            ops.append({"op": "remove", "path": u})
    except ValueError as e:
        raise SystemExit(f"kit_wave_edit: bad JSON: {e}")
    if not ops:
        raise SystemExit("kit_wave_edit: no patch (--patch, --patch-file, --set or --unset)")
    edit(a.coord, ops, a.message, dry=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
