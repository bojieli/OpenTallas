#!/usr/bin/env python3
"""wt-reaper: remove idle, clean, pushed git worktrees from the fleet scratch disks (INFRA-REAPER 2026-10-25).

Full checkouts are ~42 GB each; lanes leave them behind and they filled epyc1 scratch2 (92 % after 800 GB were freed).
Runs per host from a systemd --user timer (every 30 min).  A worktree is removed ONLY when ALL of these hold:
  1. not protected: path contains root-merge / merge-hub / closed_archive / die-ci, is a repo's main worktree, the hub
     repo (~/OpenTallas) or the coordination mirror (~/coord), or is locked (git worktree lock / an unfinished add);
  2. no live reference: no process has its cwd, root, an open fd, a mapped file or an argv word inside it (/proc, plus
     `sudo -n` for other users' processes when allowed), no docker container mounts it or a specific (non-generic) ancestor of it, no systemd --user unit
     (ot-heavy oth-* scopes name their command) and no ot-run spill_pending record names it;
  3. idle: no file or directory in the tree modified in the last --idle-h hours (find -mmin, bounded by a timeout:
     a timeout counts as busy), and the worktree's git admin files (HEAD, index, logs/HEAD) are as old;
  4. clean: `git status --porcelain` is empty, ignoring __pycache__ / *.pyc (then `worktree remove --force`), and
     at most --ignored-max-mb (100 MB) of gitignored non-cache data (build/, runs/ ... may hold lane results);
  5. pushed: `git branch -r --contains HEAD` is non-empty.
Then `git -C <repo> worktree remove [--force] <wt>` and `git worktree prune`.  Every removal is logged to
~/.local/state/wt-reaper/removals.tsv; every decision of the last run to last-run.tsv.
A DIRTY worktree idle > --dirty-report-h (24 h) is never removed: its changes (tracked diff + untracked files
<= 1 MB, via a temporary index, the lane's index is not touched) are saved once per state to
--rescue-dir/wt-reaper-<host>-<name>-<head7>-<hash8>.patch, verified non-empty, and listed in dirty.tsv for the lane.
Kills nothing.  Default is a dry run; --apply removes."""
import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOME = Path.home()
DEFAULT_ROOTS = ["/srv/opentallas-scratch2/claude", "/srv/opentallas-scratch/claude", str(HOME / "wt")]
PROTECT_SUBSTR = ["root-merge", "merge-hub", "closed_archive", "die-ci"]
PROTECT_PATHS = [str(HOME / "OpenTallas"), str(HOME / "coord")]
STATE = HOME / ".local/state/wt-reaper"
RESCUE_DIR = "/srv/opentallas-scratch2/claude/rescue"  # scratch2: /srv/opentallas-scratch is on root on epyc1
SPILL_PENDING = HOME / ".local/state/ot-run/spill_pending"
JUNK_RE = re.compile(r"(^|/)__pycache__(/|$)|\.py[co]$")
UNTRACKED_MAX = 1 << 20
IGNORED_MAX = 100 << 20  # ignored (gitignored) data above this keeps the tree: build/, runs/ etc. may be lane results
PATCH_MAX = 2 << 30  # a rescue patch above this is discarded (sparse-state artifacts made 37 GB patches on 10-25)
CACHE_RE = re.compile(r"(^|/)(__pycache__|\.pytest_cache|\.ruff_cache|\.cache|\.claude)(/|$)|\.py[cod]$")
GENERIC_MOUNTS = {"/", "/srv", "/home", "/tmp", "/var", str(HOME)}


def sh(cmd, timeout=600, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "TIMEOUT")


def git(wt, *args, timeout=900, env=None):
    return sh(["git", "--no-optional-locks", "-C", str(wt), *args], timeout=timeout, env=env)


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


# ---------------------------------------------------------------- discovery
def find_worktrees(roots, maxdepth=3):
    """[(wt_path, admin_dir, common_dir)] for every linked worktree (a dir holding a `.git` FILE) under roots."""
    out, seen = [], set()
    for root in roots:
        stack = [(Path(root), 0)]
        while stack:
            d, depth = stack.pop()
            try:
                ents = list(os.scandir(d))
            except OSError:
                continue
            g = d / ".git"
            if any(e.name == ".git" and e.is_file(follow_symlinks=False) for e in ents):
                try:
                    m = re.match(r"gitdir:\s*(.+)", g.read_text().strip())
                except OSError:
                    m = None
                if m:
                    admin = Path(m.group(1))
                    if not admin.is_absolute():
                        admin = (d / admin).resolve()
                    try:
                        common = (admin / (admin / "commondir").read_text().strip()).resolve()
                    except OSError:
                        common = admin.parent.parent
                    rp = os.path.realpath(d)
                    if rp not in seen:
                        seen.add(rp)
                        out.append((str(d), str(admin), str(common)))
                continue  # never descend into a worktree
            if depth >= maxdepth:
                continue
            for e in ents:
                if e.is_dir(follow_symlinks=False) and e.name not in (".git", "__pycache__"):
                    stack.append((Path(e.path), depth + 1))
    return sorted(out)


# ---------------------------------------------------------------- live references
def live_refs(sudo=True):
    """(paths, texts): every path a process/container holds, and every text (argv, unit lines, spill records)."""
    me = {os.getpid(), os.getppid()}
    paths, texts = set(), []
    for p in os.listdir("/proc"):
        if not p.isdigit() or int(p) in me:
            continue
        base = f"/proc/{p}"
        for link in ("cwd", "root"):
            try:
                paths.add(os.readlink(f"{base}/{link}"))
            except OSError:
                pass
        try:
            for fd in os.listdir(f"{base}/fd"):
                try:
                    paths.add(os.readlink(f"{base}/fd/{fd}"))
                except OSError:
                    pass
        except OSError:
            pass
        try:
            with open(f"{base}/maps") as f:
                for line in f:
                    parts = line.split(None, 5)
                    if len(parts) == 6 and parts[5].startswith("/"):
                        paths.add(parts[5].strip())
        except OSError:
            pass
        try:
            with open(f"{base}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
            if "wt-reaper" not in cmd:
                texts.append(cmd)
        except OSError:
            pass
    if sudo and shutil.which("sudo") and sh(["sudo", "-n", "true"], timeout=20).returncode == 0:
        r = sh(["sudo", "-n", "find", "/proc", "-mindepth", "2", "-maxdepth", "3", "(", "-path", "/proc/[0-9]*/cwd",
                "-o", "-path", "/proc/[0-9]*/root", "-o", "-path", "/proc/[0-9]*/fd/*", ")", "-printf", "%l\\n"],
               timeout=300)
        paths.update(x for x in r.stdout.splitlines() if x.startswith("/"))
    if shutil.which("docker"):
        ids = sh(["docker", "ps", "-q"], timeout=60).stdout.split()
        if ids:
            r = sh(["docker", "inspect", "--format", "{{range .Mounts}}{{.Source}}\n{{end}}", *ids], timeout=120)
            paths.update(x.strip() for x in r.stdout.splitlines() if x.strip().startswith("/"))
    r = sh(["systemctl", "--user", "list-units", "--all", "--plain", "--no-legend", "--no-pager"], timeout=60)
    texts.extend(r.stdout.splitlines())
    if SPILL_PENDING.is_dir():
        for f in SPILL_PENDING.glob("*"):
            try:
                texts.append(f.read_text(errors="replace"))
            except OSError:
                pass
    return paths, texts


def _generic(p, roots=()):
    """True for a broad ancestor (/, /srv, a scratch root, <scratch>/claude, a reaper root) that says nothing about wt"""
    p = p.rstrip("/") or "/"
    if p in GENERIC_MOUNTS or p in {r.rstrip("/") for r in roots}:
        return True
    return bool(re.fullmatch(r"/srv/[^/]+(/claude)?(/wt)?", p))


def referenced(wt, paths, texts, roots=()):
    """first live reference inside wt, or a specific (non-generic) ancestor of it such as a docker bind mount
    of a lane dir that holds the worktree (or None)"""
    cands = {wt.rstrip("/"), os.path.realpath(wt)}
    for c in cands:
        pre = c + "/"
        for p in paths:
            p = p.split(" (deleted)")[0]
            if p == c or p.startswith(pre):
                return "proc/docker path " + p
            if c.startswith(p.rstrip("/") + "/") and not _generic(p, roots) and os.path.isdir(p):
                return "ancestor in use " + p
        pat = re.compile(re.escape(c) + r"(?=$|[/\s'\";:,)])")
        for t in texts:
            if pat.search(t):
                return "live text: " + t.strip()[:160]
    return None


# ---------------------------------------------------------------- checks
def protected(wt, admin, common, extra=()):
    rp = os.path.realpath(wt)
    for s in list(PROTECT_SUBSTR) + list(extra):
        if s in wt or s in rp:
            return f"protected ({s})"
    for p in PROTECT_PATHS:
        if rp == os.path.realpath(p) or rp.startswith(os.path.realpath(p) + "/"):
            return f"protected ({p})"
    if os.path.realpath(common) == os.path.join(rp, ".git"):
        return "main worktree"
    for lock in ("locked", "initializing"):
        if os.path.exists(os.path.join(admin, lock)):
            return f"locked ({lock})"
    return None


def recently_modified(wt, admin, hours, timeout=900):
    """None if idle, else a reason string (a timeout counts as busy)."""
    cutoff = time.time() - hours * 3600
    for f in ("HEAD", "index", "logs/HEAD"):
        try:
            if os.stat(os.path.join(admin, f)).st_mtime > cutoff:
                return f"git admin {f} modified < {hours} h"
        except OSError:
            pass
    r = sh(["find", wt, "-xdev", "-mmin", f"-{int(hours * 60)}", "-print", "-quit"], timeout=timeout)
    if r.returncode == 124:
        return "find timeout (counted busy)"
    if r.stdout.strip():
        return "modified < %g h: %s" % (hours, r.stdout.strip()[len(wt):][:120] or "/")
    return None


def dirt(wt):
    """(real_lines, junk_lines) of `git status --porcelain`, or (None, err)"""
    r = git(wt, "status", "--porcelain", "--untracked-files=all")
    if r.returncode != 0:
        return None, (r.stderr.strip() or "git status failed")[:160]
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    junk = [l for l in lines if JUNK_RE.search(l[3:].strip('"'))]
    return [l for l in lines if l not in junk], junk


def ignored_bytes(wt, timeout=600):
    """(bytes, example) of gitignored data that is not a cache, or (None, err)"""
    r = git(wt, "status", "--porcelain", "--ignored=matching", "--untracked-files=normal", timeout=timeout)
    if r.returncode != 0:
        return None, (r.stderr.strip() or "git status --ignored failed")[:160]
    ign = [l[3:].strip('"') for l in r.stdout.splitlines() if l.startswith("!! ")]
    ign = [p for p in ign if not CACHE_RE.search(p.rstrip("/"))]
    if not ign:
        return 0, ""
    d = sh(["du", "-sxb", "--", *[os.path.join(wt, p) for p in ign[:2000]]], timeout=timeout)
    if d.returncode == 124:
        return None, "du timeout on ignored data"
    total, big = 0, ("", -1)
    for line in d.stdout.splitlines():
        n, _, path = line.partition("\t")
        if n.isdigit():
            total += int(n)
            if int(n) > big[1]:
                big = (path[len(wt):], int(n))
    return total, big[0]


def pushed(wt):
    r = git(wt, "branch", "-r", "--contains", "HEAD", timeout=300)
    br = [b for b in r.stdout.split() if b.startswith("origin/")] if r.returncode == 0 else []
    return bool(br), br[:1]


def rescue_patch(wt, name, rescue_dir, host):
    """Save tracked + small untracked changes via a temporary index; return (path, bytes, note)."""
    head = git(wt, "rev-parse", "HEAD").stdout.strip()
    real, _ = dirt(wt)
    key = hashlib.sha1(("\n".join(real or []) + head).encode()).hexdigest()[:8]
    out = Path(rescue_dir) / f"wt-reaper-{host}-{name}-{head[:7]}-{key}.patch"
    if out.exists() and out.stat().st_size > 0:
        return str(out), out.stat().st_size, "exists"
    gitdir = git(wt, "rev-parse", "--git-dir").stdout.strip()
    with tempfile.TemporaryDirectory() as td:
        idx = os.path.join(td, "index")
        src = os.path.join(gitdir if os.path.isabs(gitdir) else os.path.join(wt, gitdir), "index")
        if os.path.exists(src):
            shutil.copy2(src, idx)
        env = dict(os.environ, GIT_INDEX_FILE=idx)
        git(wt, "add", "-u", env=env)
        big, small = [], []
        for l in (real or []):
            if l.startswith("??"):
                p = l[3:].strip('"')
                fp = os.path.join(wt, p)
                if os.path.isfile(fp) and os.path.getsize(fp) <= UNTRACKED_MAX and len(small) < 2000:
                    small.append(p)
                else:
                    big.append(p)
        for i in range(0, len(small), 200):
            git(wt, "add", "-f", "--", *small[i:i + 200], env=env)
        Path(rescue_dir).mkdir(parents=True, exist_ok=True)
        tmp = Path(str(out) + ".part")
        # stream to disk (never into memory); -D: deletions without their content (a wiped sparse index once made
        # a 37 GB patch); abort above PATCH_MAX
        with tmp.open("wb") as fh:
            try:
                p = subprocess.Popen(["git", "--no-optional-locks", "-C", wt, "diff", "--cached", "--binary",
                                      "--irreversible-delete", "HEAD"], stdout=fh, stderr=subprocess.DEVNULL, env=env)
                t0 = time.time()
                while p.poll() is None:
                    time.sleep(1)
                    if tmp.stat().st_size > PATCH_MAX or time.time() - t0 > 1800:
                        p.kill()
                        p.wait()
                        break
            except OSError:
                pass
        ok = p.returncode == 0 and tmp.stat().st_size <= PATCH_MAX
    if not ok:
        tmp.unlink()
        return "", 0, "rescue patch failed or > %d GB (not kept)" % (PATCH_MAX >> 30)
    tmp.replace(out)
    note = f"untracked >1MB or dirs not saved: {len(big)}" if big else ""
    if big:
        Path(str(out) + ".big.txt").write_text("\n".join(big) + "\n")
    return str(out), out.stat().st_size, note


# ---------------------------------------------------------------- main
def disk_pct(path):
    try:
        u = shutil.disk_usage(path)
        return round(100.0 * (u.total - u.free) / u.total, 1)
    except OSError:
        return None


def append_tsv(path, row, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a") as f:
        if new:
            f.write("\t".join(header) + "\n")
        f.write("\t".join(str(x).replace("\t", " ").replace("\n", " ") for x in row) + "\n")


def evaluate(wt, admin, common, refs, a):
    """(verdict, reason, info) where verdict in REMOVE, REMOVE_FORCE, KEEP, DIRTY_IDLE"""
    info = {}
    why = protected(wt, admin, common, a.protect)
    if why:
        return "KEEP", why, info
    why = referenced(wt, *refs, roots=a.roots)
    if why:
        return "KEEP", why, info
    busy = recently_modified(wt, admin, a.idle_h, timeout=a.find_timeout)
    if busy:
        return "KEEP", busy, info
    real, junk = dirt(wt)
    if real is None:
        return "KEEP", "git status: " + junk, info
    if real:
        info["dirty"] = len(real)
        stale = recently_modified(wt, admin, a.dirty_report_h, timeout=a.find_timeout)
        if stale is None:
            return "DIRTY_IDLE", f"dirty ({len(real)} paths, e.g. {real[0][:80]}) idle > {a.dirty_report_h} h", info
        return "KEEP", f"dirty ({len(real)} paths, e.g. {real[0][:80]})", info
    ib, ex = ignored_bytes(wt, timeout=a.find_timeout)
    if ib is None:
        return "KEEP", "ignored data: " + ex, info
    if ib > a.ignored_max_mb * (1 << 20):
        return "KEEP", f"ignored (gitignored) data {ib >> 20} MB, e.g. {ex[:80]}", info
    ok, br = pushed(wt)
    if not ok:
        return "KEEP", "HEAD not in any origin branch", info
    info["remote"] = br[0] if br else ""
    return ("REMOVE_FORCE" if junk else "REMOVE"), f"clean{' (pycache only)' if junk else ''}, idle > {a.idle_h} h, in {info['remote']}", info


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="really remove (default: dry run)")
    ap.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS)
    ap.add_argument("--idle-h", type=float, default=2.0)
    ap.add_argument("--dirty-report-h", type=float, default=24.0)
    ap.add_argument("--find-timeout", type=int, default=900)
    ap.add_argument("--ignored-max-mb", type=float, default=IGNORED_MAX >> 20,
                    help="keep a tree holding more gitignored non-cache data than this (MB)")
    ap.add_argument("--protect", nargs="*", default=[], help="extra protected path substrings")
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--rescue-dir", default=RESCUE_DIR)
    ap.add_argument("--no-rescue", action="store_true")
    ap.add_argument("--no-sudo", action="store_true")
    a = ap.parse_args(argv)
    host = socket.gethostname()
    state = Path(a.state)
    state.mkdir(parents=True, exist_ok=True)
    import fcntl
    lockf = open(state / "lock", "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("wt-reaper: another run holds the lock; exiting")
        return 0
    roots = [r for r in a.roots if os.path.isdir(r)]
    wts = find_worktrees(roots)
    refs = live_refs(sudo=not a.no_sudo)
    hdr_run = ["time", "host", "mode", "verdict", "path", "branch", "head", "reason"]
    last = state / "last-run.tsv.tmp"
    if last.exists():
        last.unlink()
    removed, commons = 0, set()
    for wt, admin, common in wts:
        if not os.path.isdir(common):
            continue
        verdict, reason, info = evaluate(wt, admin, common, refs, a)
        head = git(wt, "rev-parse", "--short=9", "HEAD", timeout=60).stdout.strip()
        branch = git(wt, "rev-parse", "--abbrev-ref", "HEAD", timeout=60).stdout.strip()
        mode = "apply" if a.apply else "dry"
        if verdict.startswith("REMOVE") and a.apply:
            # re-check live use right before the removal
            fresh = live_refs(sudo=not a.no_sudo)
            again = referenced(wt, *fresh, roots=a.roots)
            if again:
                verdict, reason = "KEEP", "became live: " + again
            else:
                repo = os.path.dirname(common) if common.endswith("/.git") else common
                before = disk_pct(wt)
                cmd = ["git", "-C", repo, "worktree", "remove"] + (["--force"] if verdict == "REMOVE_FORCE" else []) + [wt]
                r = sh(cmd, timeout=3600)
                if r.returncode == 0:
                    removed += 1
                    commons.add(repo)
                    after = disk_pct(os.path.dirname(wt))
                    append_tsv(state / "removals.tsv",
                               [now(), host, wt, branch, head, info.get("remote", ""), verdict, reason, before, after],
                               ["time", "host", "path", "branch", "head", "remote", "how", "reason", "disk_pct_before",
                                "disk_pct_after"])
                    verdict = "REMOVED" + ("_FORCE" if verdict == "REMOVE_FORCE" else "")
                else:
                    verdict, reason = "KEEP", "worktree remove failed: " + (r.stderr.strip() or r.stdout.strip())[:160]
        if verdict == "DIRTY_IDLE" and not a.no_rescue:
            name = os.path.basename(wt.rstrip("/"))
            try:
                p, n, note = rescue_patch(wt, name, a.rescue_dir, host)
                reason += f"; rescue {p} ({n} B{', EMPTY' if n == 0 else ''}{'; ' + note if note else ''})"
                append_tsv(state / "dirty.tsv", [now(), host, wt, branch, head, p, n, note],
                           ["time", "host", "path", "branch", "head", "patch", "bytes", "note"])
            except Exception as e:  # report, never die on one tree
                reason += f"; rescue FAILED {e!r}"[:200]
        reason = " ".join(reason.split())
        append_tsv(last, [now(), host, mode, verdict, wt, branch, head, reason], hdr_run)
        print("\t".join([verdict, wt, branch, head, reason]), flush=True)
    for repo in sorted(commons):
        sh(["git", "-C", repo, "worktree", "prune"], timeout=600)
    if last.exists():
        last.replace(state / "last-run.tsv")
    pcts = {r: disk_pct(r) for r in roots}
    summary = f"{now()} {host} wt-reaper {'apply' if a.apply else 'dry'}: {len(wts)} worktrees, removed {removed}; disk % " + \
              " ".join(f"{r}={p}" for r, p in pcts.items())
    append_tsv(state / "runs.log", [summary], ["summary"])
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
