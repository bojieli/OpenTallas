#!/usr/bin/env python3
"""TREE-WRITE-GUARD (FLOW-FLEET-R1 11-22, COORD class fix): a writer of a plan tree (die_plan bind, R8 table refresh, land_r8_derive --out,
ot-build's in-place refresh) refuses a target path that resolves OUTSIDE the caller's own tree root.

Incident 11-21 20:02-22:5x: a "private" launch copy (rt_launch_tree.sh layout) had physical/die_plan as a symlink into the shared
kw45/snap_qwen_compute/qwen_compute_v2r10_famqc tree; the strict bind's R8 refresh (tmp + rename) replaced the shared runtime table on
epyc7 and epyc10.  A tmp + rename write breaks a hardlink (new inode) but follows a directory symlink, so the symlink is the hole.

  refusal(path, root=None, inplace=False) -> '' or the refusal text
    root     the caller's tree root; default = the nearest LEXICAL ancestor of path holding a tree marker (.rt_launch_ok, .fork.json,
             .src-manifest.json, .git, .ot-tree-root), else the cwd when path lies lexically under it, else nothing to judge ('').
    rule 1   realpath(path) must lie inside realpath(root): a symlinked component (dir or the file itself) that leaves the tree is refused,
             naming the first symlink on the way.
    rule 2   inplace=True (a writer that opens the existing file for writing): a regular file with nlink > 1 is refused, its inode is
             shared with another tree.  tmp + rename writers pass inplace=False: the rename gives the path a new inode.
Stdlib only, stat-only."""
import os
import sys

MARKERS = (".rt_launch_ok", ".fork.json", ".src-manifest.json", ".git", ".ot-tree-root")


def inside(p, root):
    root = root.rstrip("/") or "/"
    return p == root or root == "/" or p.startswith(root + "/")


def tree_root(path, cwd=None):
    """nearest lexical ancestor dir of PATH with a tree marker, else the cwd when PATH is lexically under it, else ''"""
    p = os.path.abspath(path)
    d = os.path.dirname(p)
    while d and d != "/":
        if any(os.path.lexists(os.path.join(d, m)) for m in MARKERS):
            return d
        d = os.path.dirname(d)
    c = os.path.abspath(cwd or os.getcwd())
    return c if c != "/" and inside(p, c) else ""


def first_link(path, root):
    """the first symlink component of lexical PATH below lexical ROOT ('' when none)"""
    p, r = os.path.abspath(path), os.path.abspath(root)
    rel = os.path.relpath(p, r)
    if rel == "." or rel.startswith(".."):
        return ""
    cur = r
    for part in rel.split(os.sep):
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            return cur
    return ""


def refusal(path, root=None, inplace=False):
    p = os.path.abspath(path)
    r = os.path.abspath(root) if root else tree_root(p)
    if r:
        rr, tgt = os.path.realpath(r), os.path.realpath(p)
        if not inside(tgt, rr):
            via = first_link(p, r)
            how = f"through symlink {via} -> {os.readlink(via)}" if via else "(not under it)"
            return (f"TREE-WRITE REFUSED {path}: resolves to {tgt}, outside the caller's tree root {r} (real {rr}) {how}. A write there changes "
                    f"another tree. Make a real private copy (ot-tree-fork SRC DST --materialize) or write to your own tree / bind OUT.")
    if inplace and os.path.isfile(p) and not os.path.islink(p):
        n = os.stat(p).st_nlink
        if n > 1:
            return (f"TREE-WRITE REFUSED {path}: in-place write to a file with nlink {n} (its inode is shared with another tree); "
                    f"write tmp + rename, or copy the file first")
    return ""


def check(path, root=None, inplace=False, who="writer"):
    """refusal -> print it and exit 3"""
    why = refusal(path, root, inplace)
    if why:
        print(f"{who}: {why}", file=sys.stderr)
        print(f"{who}: {why}")
        raise SystemExit(3)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="check that PATH (to be written) stays inside its tree root")
    ap.add_argument("path", nargs="+")
    ap.add_argument("--root")
    ap.add_argument("--inplace", action="store_true")
    a = ap.parse_args()
    bad = [w for w in (refusal(p, a.root, a.inplace) for p in a.path) if w]
    print("\n".join(bad) if bad else "TREE-WRITE OK")
    sys.exit(3 if bad else 0)
