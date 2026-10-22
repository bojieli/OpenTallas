#!/usr/bin/env python3
"""sparse_keep: widen a sparse worktree WITHOUT deleting anything that is on disk now (TOKc-SPARSE 2026-10-22).

Why: `git sparse-checkout add|set|reapply` (and checkout/merge/reset --hard) re-apply the pattern list to the WHOLE
index.  A tracked path that is on disk but matched by no pattern (a kit committed with `git add --sparse`, a file
materialized by hand for a gate, ...) is silently deleted from disk.  10-22 the S81 TOPK TX x gate died with
FileNotFoundError on physical/ref_tile/s81dv_idxtxn32x/floorplan.json: the submit waiter's
`git -C WT sparse-checkout add physical/ref_tile/s81dv_idxtxga/` re-applied the list and removed the x kit, which had
never been in that worktree's list (git 2.34 also takes `set --no-cone` literally as a pattern line).

`add WT PATH...`  adds PATH... plus every materialized-but-unlisted directory, so the re-apply removes nothing; the
                  list only grows.  Refuses (changes nothing) when it cannot protect a path without materializing
                  other files.  Verifies afterwards that every file that was on disk still is.
`protect WT`      the same with no new paths (pre-arm a worktree before someone else's `sparse-checkout add`).
`check WT`        list materialized-but-unlisted paths (exit 1 if any).

Matching follows git 2.34 unpack_trees non-cone semantics (cone-format files are valid non-cone lists): per directory
level the last matching pattern decides, UNDECIDED inherits the parent's result, the root default is NOT matched.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def git(wt, *args, check=True):
    p = subprocess.run(["git", "-C", str(wt), *args], capture_output=True, text=True, timeout=1800)
    if check and p.returncode:
        raise SystemExit(f"sparse_keep: git {' '.join(args)} failed: {p.stderr.strip()[:400]}")
    return p.stdout


# ------------------------------------------------------------------------------------------------ pattern matching
def _wild_re(pat):
    """gitignore wildmatch (WM_PATHNAME) -> regex"""
    out, i, n = [], 0, len(pat)
    while i < n:
        c = pat[i]
        if c == "*":
            if pat.startswith("**", i):
                pre_ok = i == 0 or pat[i - 1] == "/"
                j = i + 2
                if pre_ok and (j == n or pat[j] == "/"):
                    if j == n:
                        out.append(".*")
                    else:
                        out.append("(?:.*/)?")
                        j += 1
                    i = j
                    continue
                out.append("[^/]*")
                i = j
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            j = pat.find("]", i + 2)
            if j < 0:
                out.append(re.escape(c))
            else:
                body = pat[i + 1:j]
                if body[:1] in "!^":
                    body = "^" + body[1:]
                out.append("[" + body.replace("\\", "\\\\") + "]")
                i = j
        elif c == "\\" and i + 1 < n:
            i += 1
            out.append(re.escape(pat[i]))
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("".join(out) + r"\Z")


class Pattern:
    def __init__(self, line):
        p = line
        self.negative = p.startswith("!")
        if self.negative:
            p = p[1:]
        self.mustbedir = p.endswith("/")
        p = p.rstrip("/")
        self.anchored = "/" in p          # a slash anywhere but the end anchors to the root
        p = p.lstrip("/")
        self.rx = _wild_re(p)

    def match(self, path, isdir):
        if self.mustbedir and not isdir:
            return False
        return bool(self.rx.match(path if self.anchored else path.rsplit("/", 1)[-1]))


def parse_patterns(text):
    pats = []
    for ln in text.splitlines():
        ln = ln.rstrip("\n")
        if not ln.strip() or ln.startswith("#"):
            continue
        if ln.startswith("\\#") or ln.startswith("\\!"):
            ln = ln[1:]
        pats.append(Pattern(ln.rstrip()))
    return pats


def _decide(pats, path, isdir):
    for p in reversed(pats):
        if p.match(path, isdir):
            return not p.negative
    return None


def included(pats, path):
    """True when git 2.34 keeps <path> (a file) materialized under these patterns"""
    res = False
    parts = path.split("/")
    for k in range(1, len(parts)):
        d = _decide(pats, "/".join(parts[:k]), True)
        if d is not None:
            res = d
    d = _decide(pats, path, False)
    return res if d is None else d


# ------------------------------------------------------------------------------------------------ worktree state
def sparse_file(wt):
    p = Path(git(wt, "rev-parse", "--git-path", "info/sparse-checkout").strip())
    return p if p.is_absolute() else Path(wt) / p


def cone_mode(wt):
    return git(wt, "config", "--get", "core.sparseCheckoutCone", check=False).strip().lower() == "true"


def index_entries(wt):
    """[(path, skip_worktree)] of the worktree's index"""
    out = []
    for rec in git(wt, "ls-files", "-t", "-z").split("\0"):
        if len(rec) > 2:
            out.append((rec[2:], rec[0] == "S"))
    return out


def at_risk(wt, pats=None, entries=None):
    """files on disk, tracked, not skip-worktree, matched by no pattern: the next re-apply deletes them"""
    wt = Path(wt)
    if pats is None:
        f = sparse_file(wt)
        pats = parse_patterns(f.read_text() if f.is_file() else "")
    entries = index_entries(wt) if entries is None else entries
    return sorted(p for p, s in entries if not s and not included(pats, p) and (wt / p).exists())


def protect_dirs(risk, entries):
    """smallest set of directories covering <risk> that contain no skip-worktree entry (adding them materializes
    nothing new); files whose parent directory holds skip-worktree entries come back as single files"""
    skipped = [p for p, s in entries if s]
    sk_dirs = set()
    for p in skipped:
        parts = p.split("/")
        for k in range(1, len(parts)):
            sk_dirs.add("/".join(parts[:k]))
    dirs, files = set(), []
    for p in risk:
        parts = p.split("/")
        best = None
        for k in range(len(parts) - 1, 0, -1):     # climb while the directory holds no skipped entry
            d = "/".join(parts[:k])
            if d in sk_dirs:
                break
            best = d
        if best is None:
            files.append(p)
        else:
            dirs.add(best)
    dirs = {d for d in dirs if not any(d.startswith(o + "/") for o in dirs)}
    return sorted(dirs), sorted(files)


def add(wt, paths, dry_run=False):
    """add <paths> (+ protection for at-risk files) to the sparse list; returns (rc, message)"""
    wt = Path(wt)
    sf = sparse_file(wt)
    before_text = sf.read_text() if sf.is_file() else ""
    pats = parse_patterns(before_text)
    entries = index_entries(wt)
    on_disk = [p for p, s in entries if not s and (wt / p).exists()]
    risk = at_risk(wt, pats, entries)
    dirs, files = protect_dirs(risk, entries)
    cone = cone_mode(wt)
    if cone and files:
        return 1, ("REFUSED (nothing changed): cone mode cannot protect these on-disk files without materializing "
                   "their whole directory: " + ", ".join(files[:10]))
    req = [p.strip("/") for p in paths if p.strip("/")]
    if cone:
        new = req + dirs
    else:
        new = ["/" + p + ("" if git(wt, "cat-file", "-t", f"HEAD:{p}", check=False).strip() == "blob" else "/")
               for p in req] \
            + ["/" + d + "/" for d in dirs] + ["/" + f for f in files]
    if not cone:
        chk = parse_patterns(before_text + "\n" + "\n".join(new))
        left = [p for p in on_disk if not included(chk, p)]
        if left:
            return 1, "REFUSED (nothing changed): the widened list would still drop " + ", ".join(left[:10])
    msg = (f"protecting {len(risk)} materialized-but-unlisted files via {', '.join(dirs + files) or '-'}; "
           f"adding {', '.join(req) or '-'}")
    if dry_run or not new:
        return 0, ("DRY RUN: " if dry_run else "nothing to add: ") + msg
    git(wt, "sparse-checkout", "add", *new)
    after = set(parse_patterns_lines(sf.read_text()))
    lost_pat = [ln for ln in parse_patterns_lines(before_text) if ln not in after]
    gone = [p for p in on_disk if not (wt / p).exists()]
    if gone or lost_pat:
        return 2, (f"ERROR after sparse-checkout add: {len(gone)} files vanished ({', '.join(gone[:6])}); "
                   f"patterns lost: {', '.join(lost_pat[:6]) or '-'}; recover: git -C {wt} sparse-checkout add "
                   + " ".join(sorted({'/'.join(g.split('/')[:3]) for g in gone})[:10]))
    return 0, "OK " + msg


def parse_patterns_lines(text):
    return [ln.rstrip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("add", "protect", "check"))
    ap.add_argument("wt")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    wt = Path(git(a.wt, "rev-parse", "--show-toplevel").strip())
    if git(wt, "config", "--get", "core.sparseCheckout", check=False).strip().lower() != "true":
        print("sparse_keep: not a sparse checkout; nothing to do")
        return 0
    if a.cmd == "check":
        r = at_risk(wt)
        for p in r[:200]:
            print("AT RISK " + p)
        print(f"sparse_keep: {len(r)} materialized-but-unlisted files in {wt}")
        return 1 if r else 0
    rc, msg = add(wt, a.paths if a.cmd == "add" else [], dry_run=a.dry_run)
    print("sparse_keep: " + msg)
    return rc


if __name__ == "__main__":
    sys.exit(main())
