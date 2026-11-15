#!/usr/bin/env python3
"""REPO-STATE-1 11-14: reject new large or generated files before they reach main.

The repository (main + coord/state on one GitHub repo) is ~11 GB and a full clone takes ~10 GB of disk.  Most of that
is generated P&R output and evidence JSON committed over the months.  This guard stops new growth; it never rewrites
history.  A file ADDED or MODIFIED in the checked range fails when, unless a glob in tools/repo_size_allowlist.txt
matches its path (an allowlisted file still fails above --hard-mb, default 95 MB: GitHub refuses >100 MB):
  * its blob is larger than --max-mb (default 5 MB), or
  * it is a P&R / simulation database type (odb, gds, oas, def, spef, sdf, vcd, fst, saif, also .gz/.xz/.zst), or
  * it is a JSON or Verilog file (.json, .jsonl, .v, .vg, .sv, optionally compressed) larger than --gen-mb (1 MB):
    generated evidence and netlists, not hand-written source.
Put such files in /archive (AGIdock) or run scratch and commit a small manifest (path, sha256, size, host) instead.

Usage:
  repo_size_guard.py --range BASE..HEAD        objects of the range (full or blob:none clone; CI, merge queue)
  repo_size_guard.py --staged                  the index (pre-commit hook)
  repo_size_guard.py --paths F [F ...]         working-tree files
Exit 1 when any file is rejected; prints one line per rejection.  stdlib only, python3 -I.
"""
import argparse, fnmatch, os, re, subprocess as S, sys

DB_EXT = re.compile(r"\.(odb|gds|gds2|gdsii|oas|oasis|def|spef|sdf|vcd|fst|saif)(\.(gz|xz|zst|bz2))?$", re.I)
GEN_EXT = re.compile(r"\.(json|jsonl|v|vg|sv|nl\.v)(\.(gz|xz|zst|bz2))?$", re.I)
HERE = os.path.dirname(os.path.abspath(__file__))


def git(*a, inp=None):
    r = S.run(["git", *a], input=inp, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout


def load_allow(p):
    out = []
    try:
        for ln in open(p):
            ln = ln.split("#", 1)[0].strip()
            if ln:
                out.append(ln)
    except FileNotFoundError:
        pass
    return out


def allowed(path, allow):
    return any(fnmatch.fnmatchcase(path, g) or path.startswith(g.rstrip("/") + "/") for g in allow)


def verdict(path, size, max_b, gen_b):
    """why PATH of SIZE bytes is rejected (allowlist not applied), or None"""
    if size > max_b:
        return f"{size / 1e6:.1f} MB > {max_b / 1e6:g} MB"
    if DB_EXT.search(path):
        return "generated P&R/simulation database type"
    if GEN_EXT.search(path) and size > gen_b:
        return f"generated JSON/netlist {size / 1e6:.1f} MB > {gen_b / 1e6:g} MB"
    return None


def from_range(rng):
    rows = []
    out = git("diff", "--raw", "--no-abbrev", "-z", "--no-renames", "--diff-filter=AM", rng)
    parts = out.split("\0")
    i = 0
    shas = []
    while i < len(parts) - 1:
        meta, path = parts[i], parts[i + 1]
        i += 2
        f = meta.split()
        if len(f) < 5 or f[1] == "160000":         # submodule
            continue
        shas.append((f[3], path))
    if not shas:
        return rows
    sizes = git("cat-file", "--batch-check=%(objectname) %(objectsize)", inp="".join(s + "\n" for s, _ in shas))
    sz = dict(ln.split() for ln in sizes.splitlines() if len(ln.split()) == 2)
    for s, p in shas:
        rows.append((p, int(sz.get(s, 0))))
    return rows


def from_staged():
    out = git("diff", "--cached", "--raw", "--no-abbrev", "-z", "--no-renames", "--diff-filter=AM")
    parts = out.split("\0")
    shas = [(parts[i].split()[3], parts[i + 1]) for i in range(0, len(parts) - 1, 2) if len(parts[i].split()) >= 5]
    if not shas:
        return []
    sizes = git("cat-file", "--batch-check=%(objectname) %(objectsize)", inp="".join(s + "\n" for s, _ in shas))
    sz = dict(ln.split() for ln in sizes.splitlines() if len(ln.split()) == 2)
    return [(p, int(sz.get(s, 0))) for s, p in shas]


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--range")
    g.add_argument("--staged", action="store_true")
    g.add_argument("--paths", nargs="+")
    ap.add_argument("--max-mb", type=float, default=5.0)
    ap.add_argument("--gen-mb", type=float, default=1.0)
    ap.add_argument("--hard-mb", type=float, default=95.0)
    ap.add_argument("--allowlist", default=os.path.join(HERE, "repo_size_allowlist.txt"))
    a = ap.parse_args(argv)
    allow = load_allow(a.allowlist)
    if a.range:
        rows = from_range(a.range)
    elif a.staged:
        rows = from_staged()
    else:
        rows = [(p, os.path.getsize(p)) for p in a.paths if os.path.isfile(p)]
    bad = 0
    for p, size in rows:
        why = verdict(p, size, a.max_mb * 1e6, a.gen_mb * 1e6)
        if size > a.hard_mb * 1e6:
            why = f"{size / 1e6:.1f} MB > hard cap {a.hard_mb:g} MB (allowlist does not apply)"
        elif why and allowed(p, allow):
            why = None
        if why:
            bad += 1
            print(f"REJECT {p}: {why}")
    print(f"repo_size_guard: {len(rows)} files checked, {bad} rejected"
          + ("" if not bad else " (archive them and commit a manifest, or add a reviewed glob to tools/repo_size_allowlist.txt)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
