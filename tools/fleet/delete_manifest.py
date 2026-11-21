#!/usr/bin/env python3
"""delete_manifest.py -- a per-file record of every tree ot-delete / ot-auto-retire removes (FLOW-OPS-0900, COORD 11-21, FLEET-WATCH-R7 4524dcc726).

Why: on 11-18 ot-auto-retire on epyc2 removed fable-pd-head-clk (it held ca2/ring_declared.json, later a HEAD bind input) and 126 other idle trees
under the owner-approved aggressive cleanup, and no file list was kept, so the lost input could not be named or restored from a sister copy.

Before a tree is removed, write(tree, tool) stores one gzip JSON-lines file
    ~/.local/state/delete-manifests/<YYYY-MM-DD>/<HHMMSS>-<tool>-<tree as name>.jsonl.gz
line 1: {"schema", "tree", "tool", "host", "lane", "time", "realpath"}; then one line per entry, paths relative to the tree:
    {"p": rel, "size": bytes, "sha256": hex}          a regular file under 50 MB (OT_DELETE_MANIFEST_SHA_MAX_MB)
    {"p": rel, "size": bytes, "sha256": null, "why": "large" | "budget" | "unreadable"}
    {"p": rel, "link": target}                        a symlink (never followed)
last line: {"end": true, "files": n, "bytes": total, "hashed": n, "truncated": bool}
Hashing stops after OT_DELETE_MANIFEST_HASH_S seconds (default 900) per tree; the rest is still listed with size.
This is a record only: it never refuses, never raises, and a failure to write it never changes what is deleted (owner: no new restrictive rule).
OT_DELETE_MANIFEST_DIR overrides the directory; without it, trees outside /srv are not recorded (test temp dirs).
CLI: delete_manifest.py find PATH_SUBSTRING [DAYS]   -> manifest lines naming it (to find which deleted tree held a file)
"""
import gzip
import hashlib
import json
import os
import re
import socket
import sys
import time

SCHEMA = "opentallas.delete_manifest/1"


def root_dir():
    return os.environ.get("OT_DELETE_MANIFEST_DIR") or os.path.expanduser("~/.local/state/delete-manifests")


def _sha(path, cap):
    h = hashlib.sha256()
    with open(path, "rb", buffering=0) as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write(tree, tool, sha_max_mb=None, budget_s=None, exclude=()):
    """-> manifest path, or None (not recorded / failed).  Never raises."""
    try:
        tree = os.path.abspath(tree)
        if not os.environ.get("OT_DELETE_MANIFEST_DIR") and not tree.startswith("/srv/"):
            return None
        sha_max = int(float(sha_max_mb if sha_max_mb is not None else os.environ.get("OT_DELETE_MANIFEST_SHA_MAX_MB", "50")) * 2**20)
        budget = float(budget_s if budget_s is not None else os.environ.get("OT_DELETE_MANIFEST_HASH_S", "900"))
        day, hms = time.strftime("%Y-%m-%d"), time.strftime("%H%M%S")
        d = os.path.join(root_dir(), day)
        os.makedirs(d, exist_ok=True)
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", tree.strip("/"))[-150:]
        out = os.path.join(d, f"{hms}-{re.sub(r'[^A-Za-z0-9_-]+', '_', tool)}-{name}.jsonl.gz")
        tmp = out + f".tmp{os.getpid()}"
        t0 = time.time()
        n = total = hashed = 0
        truncated = False
        with gzip.open(tmp, "wt") as fh:
            fh.write(json.dumps({"schema": SCHEMA, "tree": tree, "tool": tool, "host": socket.gethostname().split(".")[0],
                                 "lane": os.environ.get("OT_LANE", ""), "time": time.strftime("%F %T %Z"),
                                 "realpath": os.path.realpath(tree)}) + "\n")
            if os.path.islink(tree) or not os.path.isdir(tree):
                walk = [(os.path.dirname(tree), [], [os.path.basename(tree)])]
                base = os.path.dirname(tree)
            else:
                walk = os.walk(tree, followlinks=False)
                base = tree
            for dp, dns, fns in walk:
                rel_dp = os.path.relpath(dp, base)
                if rel_dp == "." and exclude:
                    dns[:] = [x for x in dns if x not in exclude]
                    fns = [x for x in fns if x not in exclude]
                for x in [x for x in dns if os.path.islink(os.path.join(dp, x))] + list(fns):
                    p = os.path.join(dp, x)
                    rel = os.path.normpath(os.path.join(rel_dp, x))
                    try:
                        if os.path.islink(p):
                            fh.write(json.dumps({"p": rel, "link": os.readlink(p)}) + "\n")
                            continue
                        st = os.lstat(p)
                    except OSError:
                        fh.write(json.dumps({"p": rel, "size": None, "sha256": None, "why": "unreadable"}) + "\n")
                        continue
                    n += 1
                    total += st.st_size
                    rec = {"p": rel, "size": st.st_size}
                    if st.st_size >= sha_max:
                        rec.update(sha256=None, why="large")
                    elif time.time() - t0 > budget:
                        rec.update(sha256=None, why="budget")
                        truncated = True
                    else:
                        try:
                            rec["sha256"] = _sha(p, sha_max)
                            hashed += 1
                        except OSError:
                            rec.update(sha256=None, why="unreadable")
                    fh.write(json.dumps(rec) + "\n")
            fh.write(json.dumps({"end": True, "files": n, "bytes": total, "hashed": hashed, "truncated": truncated}) + "\n")
        os.replace(tmp, out)
        return out
    except Exception as e:                       # noqa: BLE001 - a record, never a stop
        print(f"delete_manifest: not written for {tree}: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def find(sub, days=30):
    """-> [(manifest, tree, line)] entries whose tree/relative path contains SUB, newest first"""
    out = []
    r = root_dir()
    cut = time.time() - days * 86400
    try:
        dirs = sorted(os.listdir(r), reverse=True)
    except OSError:
        return out
    for dd in dirs:
        for f in sorted(os.listdir(os.path.join(r, dd)), reverse=True):
            m = os.path.join(r, dd, f)
            if not f.endswith(".jsonl.gz") or os.path.getmtime(m) < cut:
                continue
            try:
                with gzip.open(m, "rt") as fh:
                    head = json.loads(fh.readline())
                    for ln in fh:
                        rec = json.loads(ln)
                        if "p" in rec and sub in os.path.join(head.get("tree", ""), rec["p"]):
                            out.append((m, head.get("tree"), rec))
            except (OSError, ValueError, EOFError):
                continue
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "find":
        for m, t, rec in find(a[1], float(a[2]) if len(a) > 2 else 30):
            print(f"{m}\t{t}\t{json.dumps(rec)}")
        sys.exit(0)
    print(__doc__)
    sys.exit(2)
