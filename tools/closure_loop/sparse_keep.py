#!/usr/bin/env python3
"""sparse_keep: widen a sparse worktree WITHOUT deleting anything that is on disk now (TOKc-SPARSE 2026-10-22).

Why: `git sparse-checkout add|set|reapply` (and checkout/merge/reset --hard) re-apply the pattern list to the WHOLE
index.  A tracked path that is on disk but matched by no pattern (a kit committed with `git add --sparse`, a file
materialized by hand for a gate, ...) is silently deleted from disk.  10-22 the S81 TOPK TX x gate died with
FileNotFoundError on physical/ref_tile/s81dv_idxtxn32x/floorplan.json: the submit waiter's
`git -C WT sparse-checkout add physical/ref_tile/s81dv_idxtxga/` re-applied the list and removed the x kit, which had
never been in that worktree's list (git 2.34 also takes `set --no-cone` literally as a pattern line).

`add WT PATH...`  appends PATH... plus every materialized-but-unlisted directory to the list file (existing lines kept
                  VERBATIM: order, negatives, comments; atomic write + .bak copy), then `git sparse-checkout reapply`
                  (never `sparse-checkout add`, which in git 2.34 rewrites/normalises non-cone lists and dropped
                  negatives 10-22).  Cone mode appends only valid cone entries or refuses.  Refuses (changes nothing)
                  when a tracked on-disk file or any untracked/ignored file would lose inclusion.  Verifies afterwards
                  that the list is unchanged and every tracked/untracked/ignored file that was on disk still is.
                  Full checkouts (core.sparseCheckout off, no/unreadable list, nothing skip-worktree): no-op, exit 0.
`protect WT`      the same with no new paths (pre-arm a worktree before someone else's `sparse-checkout add`).
`check WT`        list materialized-but-unlisted paths (exit 1 if any).

Matching follows git 2.34 unpack_trees non-cone semantics (cone-format files are valid non-cone lists): per directory
level the last matching pattern decides, UNDECIDED inherits the parent's result, the root default is NOT matched.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time
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


def untracked(wt):
    """untracked + ignored files on disk (git ls-files --others without excludes = both)"""
    return [p for p in git(wt, "ls-files", "--others", "-z").split("\0") if p]


def read_sparse(wt):
    """(path, text) of the worktree's sparse list, or (path, None) when missing/unreadable"""
    try:
        sf = sparse_file(wt)
        return sf, sf.read_text()
    except (OSError, UnicodeDecodeError, SystemExit):
        return None, None


def _cone_lines(existing_lines, path):
    """cone entries to append so <path>/ is recursive; [] when already covered; None when the list is not cone"""
    stripped = {ln.strip() for ln in existing_lines}
    if "/*" not in stripped or "!/*/" not in stripped:
        return None
    parts = path.split("/")
    recursive = lambda d: f"/{d}/" in stripped and f"!/{d}/*/" not in stripped   # noqa: E731
    out = []
    for k in range(1, len(parts)):
        d = "/".join(parts[:k])
        if recursive(d):
            return []
        if f"/{d}/" not in stripped:
            out += [f"/{d}/", f"!/{d}/*/"]
    if recursive(path):
        return []
    if f"/{path}/" in stripped:        # present as a parent entry: making it recursive would need a line removed
        return None
    return out + [f"/{path}/"]


def _atomic_write(sf, text):
    tmp = sf.with_name(sf.name + f".sparse_keep.{os.getpid()}.tmp")
    tmp.write_text(text)
    os.replace(tmp, sf)


def add(wt, paths, dry_run=False):
    """append <paths> (+ protection for at-risk files) to the sparse list, keeping every existing line verbatim, then
    `git sparse-checkout reapply`.  Returns (rc, message): 0 ok/no-op, 1 refused (nothing changed), 2 post-check fail"""
    wt = Path(wt)
    sf, before_text = read_sparse(wt)
    if before_text is None:
        return 0, "not sparse / nothing to protect (no readable sparse-checkout file)"
    entries = index_entries(wt)
    if not any(s for _, s in entries):
        return 0, "not sparse / nothing to protect (every index entry is on disk)"
    pats = parse_patterns(before_text)
    old_lines = before_text.splitlines()
    on_disk = [p for p, s in entries if not s and (wt / p).exists()]
    risk = at_risk(wt, pats, entries)
    dirs, files = protect_dirs(risk, entries)
    cone = cone_mode(wt)
    req = [p.strip("/") for p in paths if p.strip("/")]
    # requested paths already fully included need nothing
    req = [r for r in req if not all(included(pats, p) for p, _ in entries if p == r or p.startswith(r + "/"))]
    new = []
    if cone:
        if files:
            return 1, ("REFUSED (nothing changed): cone mode cannot protect these on-disk files without materializing "
                       "their whole directory: " + ", ".join(files[:10]))
        for d in req + dirs:
            if git(wt, "cat-file", "-t", f"HEAD:{d}", check=False).strip() == "blob":
                return 1, f"REFUSED (nothing changed): cone mode takes directories only, {d} is a file"
            add_l = _cone_lines(old_lines + new, d)
            if add_l is None:
                return 1, (f"REFUSED (nothing changed): cannot append a valid cone entry for {d} (list is not a "
                           "well-formed cone list, or the directory is a parent entry); widen it by hand")
            new += add_l
    else:
        for p in req:
            new.append("/" + p + ("" if git(wt, "cat-file", "-t", f"HEAD:{p}", check=False).strip() == "blob" else "/"))
        new += ["/" + d + "/" for d in dirs] + ["/" + f for f in files]
    have = {ln.strip() for ln in old_lines}
    new = [ln for i, ln in enumerate(new) if ln not in have and ln not in new[:i]]
    if not new:
        return 0, f"nothing to add: {len(risk)} at-risk files, requested paths already included"
    new_text = before_text + ("" if before_text.endswith("\n") or not before_text else "\n") + "\n".join(new) + "\n"
    chk = parse_patterns(new_text)
    left = [p for p in on_disk if not included(chk, p)]
    if left:
        return 1, "REFUSED (nothing changed): the widened list would still drop tracked " + ", ".join(left[:10])
    unt = untracked(wt)
    lose = [p for p in unt if included(pats, p) and not included(chk, p)]
    if lose:
        return 1, (f"REFUSED (nothing changed): {len(lose)} untracked/ignored files lie in paths that lose inclusion: "
                   + ", ".join(lose[:10]))
    newly = [p for p, s in entries if s and included(chk, p)]
    msg = (f"protecting {len(risk)} materialized-but-unlisted files via {', '.join(dirs + files) or '-'}; "
           f"adding {', '.join(req) or '-'}; appending {len(new)} lines; materializes {len(newly)} files")
    if dry_run:
        return 0, "DRY RUN: " + msg + "\n  + " + "\n  + ".join(new)
    bak = sf.with_name(sf.name + time.strftime(".bak.%Y%m%d-%H%M%S"))
    shutil.copy2(sf, bak)
    _atomic_write(sf, new_text)
    rp = subprocess.run(["git", "-C", str(wt), "sparse-checkout", "reapply"], capture_output=True, text=True,
                        timeout=1800)
    after_text = sf.read_text()
    lost_lines = after_text != new_text
    gone = [p for p in on_disk if not (wt / p).exists()]
    gone_unt = [p for p in unt if not os.path.lexists(wt / p)]
    if rp.returncode or lost_lines or gone or gone_unt:
        return 2, (f"ERROR after reapply (rc {rp.returncode}: {rp.stderr.strip()[:200]}): list rewritten={lost_lines}; "
                   f"{len(gone)} tracked files vanished ({', '.join(gone[:6])}); {len(gone_unt)} untracked/ignored "
                   f"vanished ({', '.join(gone_unt[:6])}); backup list {bak}")
    return 0, f"OK {msg}; backup {bak}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("add", "protect", "check"))
    ap.add_argument("wt")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    wt = Path(git(a.wt, "rev-parse", "--show-toplevel").strip())
    if git(wt, "config", "--get", "core.sparseCheckout", check=False).strip().lower() != "true":
        print("sparse_keep: not sparse / nothing to protect (core.sparseCheckout is not true)")
        return 0
    if read_sparse(wt)[1] is None:
        print("sparse_keep: not sparse / nothing to protect (no readable sparse-checkout file)")
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
