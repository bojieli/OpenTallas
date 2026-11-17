#!/usr/bin/env python3 -I
"""overlay_classify.py -- WAVE-FLOW-R2 11-17 (COORD r610): classify the tools overlay paths of a die tree that main also changed.

A tree = one main sha (its base) + overlay files.  When main moved past the base and changed an overlaid path, the tools-only refresh must know whether
the overlay is still a private patch.  For every overlay path that main changed since the base, against the hub's full repo (no -S / -G):
  (a) MAIN-HAS-IT   the overlay blob equals some version of that file in main's history (git log --raw blob ids)  -> main wins, logged
  (b) CONTAINED     the overlay's change against its base (difflib opcodes) is contained in main's current file: every replacement block is present
                    in it and every deleted block is gone                                                          -> main wins, logged
  (c) PRIVATE       anything else (also: main deleted the file)  -> NEEDS-LANE with the diff

    overlay_classify.py [--cfg kit_wave.json] [--repo GIT_DIR] [--main main] [--die D ...]       report only: counts per die + one line per path
"""
import argparse
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tools_lag as TL  # noqa: E402

MAX_DIFF = 3000
TOOL_PATHS = ("tools", "physical/common_flow")          # the paths a tools-only refresh packs; overlays elsewhere (rtl, plans) never clash with it


def git(repo, *args, data=None):
    r = subprocess.run(["git", "--git-dir", str(repo), *args], input=data, capture_output=True, timeout=300)
    if r.returncode:
        raise ValueError(f"git {' '.join(args[:2])}: {r.stderr.decode(errors='replace').strip()[:200]}")
    return r.stdout


def blob_sha1(data):
    import hashlib
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def blob_history(repo, main, paths, since=None):
    """{path: set of every blob id the file had in main's history}: ONE git log --raw call for all paths (no pickaxe)"""
    ids = {p: set() for p in paths}
    if not paths:
        return ids
    # one pass over the history of the directories the paths live in (a pathspec per file made git walk once per path: minutes for 170 files)
    dirs = sorted({p.split("/")[0] if "/" not in p.split("/", 1)[1:] and p.count("/") < 2 else "/".join(p.split("/")[:2]) for p in paths})
    out = git(repo, "log", "-m", f"{since}..{main}" if since else main, "--format=", "--raw", "--no-abbrev", "--", *dirs).decode(errors="replace")
    for ln in out.splitlines():
        if not ln.startswith(":") or "\t" not in ln:
            continue
        head, path = ln.split("\t", 1)
        f = head.split()
        if path in ids and len(f) >= 5:
            ids[path].add(f[3])
    return ids


def blob_ids(repo, main, path):
    return blob_history(repo, main, [path])[path]


def batch_show(repo, rev, paths):
    """{path: bytes | None} of `rev:path` through one git cat-file --batch process"""
    if not paths:
        return {}
    req = "".join(f"{rev}:{p}\n" for p in paths).encode()
    out = git(repo, "cat-file", "--batch", data=req)
    res, i = {}, 0
    for p in paths:
        j = out.index(b"\n", i)
        hdr = out[i:j].split()
        if len(hdr) == 2 and hdr[1] == b"missing":
            res[p] = None
            i = j + 1
            continue
        n = int(hdr[2])
        res[p] = out[j + 1:j + 1 + n]
        i = j + 1 + n + 1
    return res


def show(repo, rev, path):
    return batch_show(repo, rev, [path])[path]


def contained(base_lines, over_lines, main_lines):
    """True when every changed block of base->overlay is already in main: replacement blocks present contiguously, deleted blocks absent"""
    main_text = "\n".join(main_lines)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base_lines, over_lines, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        new = "\n".join(over_lines[j1:j2])
        old = "\n".join(base_lines[i1:i2])
        if new and new not in main_text:
            return False
        if not new and old and old in main_text:          # a pure deletion main still has
            return False
        if new and old and old in main_text and old not in new:   # replaced text that main still carries next to the replacement
            return False
    return True


def classify_path(repo, base, main, path, overlay, history=None, base_blob="?", cur="?", full_history=None):
    """-> dict(cls 'a' | 'b' | 'c', why, diff).  overlay = the overlay file bytes; history (blob ids since the base) / base_blob / cur / full_history()
    (blob ids of the whole history, only asked for when (a) on the range and (b) both fail) may be passed in (batched by classify_tree)"""
    history = blob_ids(repo, main, path) if history is None else history
    cur = show(repo, main, path) if cur == "?" else cur
    b = show(repo, base, path) if base_blob == "?" else base_blob
    oid = blob_sha1(overlay)
    if cur is not None and overlay == cur:        # r612: byte-equal to main HEAD (the blob may exist only in a hand-resolved merge commit, which a plain git log --raw omits)
        return dict(cls="a", why="overlay is byte-equal to main's current file")
    if oid in history or (b is not None and oid == blob_sha1(b)):
        return dict(cls="a", why="overlay blob " + oid[:12] + " is a version of the file in main's history")
    if cur is None:
        return dict(cls="c", why="main deleted the file", diff="")
    if b is not None:
        bl = b.decode(errors="replace").splitlines()
        ol = overlay.decode(errors="replace").splitlines()
        cl = cur.decode(errors="replace").splitlines()
        if contained(bl, ol, cl):
            return dict(cls="b", why="the overlay's change against its base is contained in main's current file")
    if full_history is not None and oid in full_history().get(path, ()):
        return dict(cls="a", why="overlay blob " + oid[:12] + " is an older version of the file in main's history")
    ref = (b or b"").decode(errors="replace").splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(ref, overlay.decode(errors="replace").splitlines(keepends=True), f"base/{path}", f"overlay/{path}", n=2))
    return dict(cls="c", why="private patch: the change is not in main", diff=diff[:MAX_DIFF])


def clash_paths(repo, base, main, overlay_paths):
    """overlay paths main changed between base and main"""
    out = git(repo, "diff", "--name-only", "-z", base, main, "--", *overlay_paths).decode().split("\0") if overlay_paths else []
    return sorted(p for p in out if p)


def in_scope(path, prefixes):
    return not prefixes or any(path == x or path.startswith(x + "/") for x in prefixes)


def classify_tree(repo, manifest, read_overlays, main="main", prefixes=TOOL_PATHS):
    """{path: result} for the clashing overlay paths of a tree manifest; read_overlays(paths) -> {path: bytes | None} (the overlay files in the tree)"""
    base = manifest["main_sha"]
    paths = sorted(p for p in (manifest.get("overlay") or {}) if in_scope(p, prefixes))
    clash = clash_paths(repo, base, main, paths)
    hist, cur, bas, data = blob_history(repo, main, clash, since=base), batch_show(repo, main, clash), batch_show(repo, base, clash), read_overlays(clash)
    full = {}

    def full_history():                  # the whole-history pass (about a minute on the hub repo) only when something is left over
        if not full:
            full.update(blob_history(repo, main, clash))
        return full
    res = {}
    for p in clash:
        d = data.get(p)
        res[p] = dict(cls="c", why="overlay file unreadable in the tree", diff="") if d is None else \
            classify_path(repo, base, main, p, d, hist[p], bas[p], cur[p], full_history)
    return res


def counts(res):
    return {k: sum(1 for v in res.values() if v["cls"] == k) for k in "abc"}


def ssh_read(host, tree):
    """read_overlays(paths) -> {path: bytes | None}: one tar stream from the tree (ssh to the gen host, or local)"""
    import io
    import tarfile

    def read(paths):
        if not paths:
            return {}
        listing = "\n".join(paths) + "\n"
        cmd = f"cd {tree} && tar cf - -T -"
        argv = ["bash", "-c", cmd] if host in (None, "", "localhost", "hub") else \
            ["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", host, cmd]
        r = subprocess.run(argv, input=listing.encode(), capture_output=True, timeout=600)
        out = {p: None for p in paths}
        try:
            with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
                for m in tf:
                    if m.isfile() and m.name in out:
                        out[m.name] = tf.extractfile(m).read()
        except tarfile.TarError:
            pass
        return out
    return read


def tree_manifest(host, tree):
    argv = ["bash", "-c", f"cat {tree}/.src-manifest.json"] if host in (None, "", "localhost", "hub") else \
        ["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", host, f"cat {tree}/.src-manifest.json"]
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise ValueError("manifest unreadable: " + r.stderr.strip()[:200])
    return json.loads(r.stdout)


def classify_die(repo, d, main="main", prefixes=TOOL_PATHS):
    host = d.get("gen_host") or (d.get("gen_hosts") or [None])[0]
    return classify_tree(repo, tree_manifest(host, d["src"]), ssh_read(host, d["src"]), main, prefixes)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--cfg", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    ap.add_argument("--repo", default=TL.DEFAULT_REPO)
    ap.add_argument("--main", default="main")
    ap.add_argument("--die", action="append")
    ap.add_argument("--diffs", action="store_true")
    ap.add_argument("--all-paths", action="store_true", help="also overlays outside tools/ and physical/common_flow (rtl, plans)")
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.cfg).read_text())
    for die in a.die or [d for d, v in cfg["dies"].items() if v.get("enabled")]:
        try:
            res = classify_die(a.repo, cfg["dies"][die], a.main, None if a.all_paths else TOOL_PATHS)
        except (ValueError, OSError, KeyError, subprocess.TimeoutExpired) as e:
            print(f"OVERLAY {die} unmeasured: {e}")
            continue
        c = counts(res)
        print(f"OVERLAY {die} clash {len(res)}: (a) main has it {c['a']}, (b) contained {c['b']}, (c) private {c['c']}")
        for p, v in res.items():
            print(f"  {v['cls']} {p}: {v['why']}")
            if a.diffs and v["cls"] == "c" and v.get("diff"):
                print("\n".join("      " + x for x in v["diff"].splitlines()[:40]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
