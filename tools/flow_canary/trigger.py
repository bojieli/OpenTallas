#!/usr/bin/env python3
"""flow_canary trigger: submit the die canaries when main changes a flow tool (systemd user timer on epyc1).

    trigger.py --src /srv/opentallas-scratch2/claude/wt/flow-canary [--root RUNS] [--state FILE] [--dry] [--force]

Fetches origin/main into the canary worktree (a detached, sparse checkout owned by FLOW-CANARY), and when any commit
since the last canaried main touches a path in canaries.json "watch", checks the worktree out at the new main and runs
`canary.py submit` for every die whose previous canary is not still running.  State: last canaried sha + per-die run.
"""
import argparse
import importlib.util
import fnmatch
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_watch_spec = importlib.util.spec_from_file_location("flow_canary_watch", HERE / "flow_watch.py")
_watch_module = importlib.util.module_from_spec(_watch_spec)
_watch_spec.loader.exec_module(_watch_module)
flow_paths = _watch_module.flow_paths
STATE = Path.home() / ".local/state/flow_canary/state.json"
LIVE_S = 12 * 3600
LOCK_REASON = "FLOW-CANARY live source; release after all referencing clients finish"


def git(src, *a):
    return subprocess.run(["git", "-C", str(src), *a], text=True, capture_output=True)


def touched(paths, watch):
    return sorted({p for p in paths for w in watch if fnmatch.fnmatch(p, w)})


def is_ab_candidate(meta):
    """FLOW-SHARED-6 2026-10-27: a candidate-branch A/B canary (source snapshot under flow-canary/ab/) is not a main
    reference run; it never blocks main's canary of the same die (main 47ce1af8bc got 1/7 canaries while A/B runs of
    f9d9190f11 / 15c4459bb3 were live)."""
    return "/flow-canary/ab/" in str(meta.get("src", ""))


def mutable_source(meta):
    """FLOW-SHARED-9 (COORD 10-27 19:36 (3)): canaries run from immutable commits only.  A run whose source is not a
    commit snapshot (flow-canary/sources/<sha> for main, flow-canary/ab/sources/<sha> for A/B) -- e.g. one submitted
    from a lane worktree such as wt/qk-cores-6 that kept moving under it -- is neither a reference nor blocks the
    trigger.  Legacy metadata without a src keeps the old behaviour."""
    src = str(meta.get("src", "") or "")
    return bool(src) and "/flow-canary/sources/" not in src and "/flow-canary/ab/sources/" not in src


def live_dies(root, now=None):
    """Uncollected transient clients never expire into permission for a duplicate.

    A missing verdict also covers an interrupted client whose remote worker survived;
    its result must be collected before another reference is submitted. Legacy run
    metadata without a client unit retains the old age fallback.
    """
    now = now or time.time()
    out = set()
    for d in glob.glob(f"{root}/*/canary_meta.json"):
        run = Path(d).parent
        if (run / "canary.json").exists():
            continue
        m = json.loads(Path(d).read_text())
        if is_ab_candidate(m) or mutable_source(m):
            continue
        if m.get("client_unit") or now - run.stat().st_mtime < LIVE_S:
            out.add(m["spec"]["die"])
    return out


def source_lock_file(source):
    p = Path(source) / ".git"
    if not p.is_file():
        return None
    text = p.read_text().strip()
    if not text.startswith("gitdir: "):
        return None
    admin = Path(text[8:])
    if not admin.is_absolute():
        admin = p.parent / admin
    return admin / "locked"


def protect_source(repo, source):
    lock = source_lock_file(source)
    if lock and lock.exists():
        return
    r = git(repo, "worktree", "lock", "--reason", LOCK_REASON, str(source))
    if r.returncode:
        raise RuntimeError(r.stderr)


def unlock_completed_sources(repo, root):
    """Reaper may remove a snapshot only after all its reference records and clients finish."""
    groups = {}
    for p in Path(root).glob("*/canary_meta.json"):
        try:
            m = json.loads(p.read_text())
            groups.setdefault(m["src"], []).append((p.parent, m))
        except (OSError, ValueError, KeyError):
            continue
    released = []
    for source, entries in groups.items():
        lock = source_lock_file(source)
        if not lock or not lock.exists() or not lock.read_text().startswith(LOCK_REASON):
            continue
        if not all((p / "canary.json").is_file() for p, _ in entries):
            continue
        units = {m.get("client_unit") for _, m in entries} - {None, ""}
        if any(subprocess.run(["systemctl", "--user", "is-active", "--quiet", u],
                              capture_output=True).returncode == 0 for u in units):
            continue
        r = git(repo, "worktree", "unlock", source)
        if r.returncode == 0:
            released.append(source)
    return released


def hold_sparse(dest):
    """FLOW-16 10-31: keep a snapshot clean.  A job run with GIT_DIR=<snapshot>/.git (hbm_sram: gen_env) makes its cwd
    the work tree, so git sees the macro files that job unpacked from `git archive` as "present outside the sparse
    patterns", clears their skip-worktree bits in the SHARED snapshot index, and the snapshot then reads ' D' for every
    later job (KV core gen: "kit provenance needs a clean, committed source checkout").  The per-worktree setting stops
    that; reapply repairs an index that was already flipped.  Only index bits change, no tracked file is rewritten."""
    for args in (("config", "--worktree", "sparse.expectFilesOutsideOfPatterns", "true"), ("sparse-checkout", "reapply")):
        r = git(dest, *args)
        if r.returncode:
            raise RuntimeError(r.stderr)


def source_snapshot(src, sha, root):
    """An immutable sparse source per revision; no checkout underneath any live canary."""
    dest = Path(root).parent / "sources" / sha[:12]
    if dest.exists():
        head = git(dest, "rev-parse", "HEAD")
        if head.returncode or head.stdout.strip() != sha:
            raise RuntimeError(f"canary source snapshot {dest} is not pinned to {sha}")
        protect_source(src, dest)
        hold_sparse(dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = git(src, "worktree", "add", "--no-checkout", "--detach", str(dest), sha)
    if r.returncode:
        raise RuntimeError(r.stderr)
    protect_source(src, dest)
    patterns = "/*\n!/results/\n!/docs/\n!/.qscratch/\n!/physical/\n/physical/die_plan/\n/physical/common_flow/\n/physical/ref_tile/\n!/physical/ref_tile/*/\n!/physical/die_plan/*/cores/harden/results/\n"
    r = subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", "--no-cone", "--stdin"],
                       input=patterns, text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    r = git(dest, "checkout", "--detach", sha)
    if r.returncode:
        raise RuntimeError(r.stderr)
    hold_sparse(dest)
    return dest


def ready_dies(src, new, specs, watch, state, busy, force=False, spec=None):
    """One slow reference holds only its own die; remember each die's submitted revision."""
    revisions = dict(state.get("die_sha", {}))
    ready, hits_all = [], set()
    for die in specs:
        old = revisions.get(die, state.get("last_sha"))
        if die in busy:
            continue
        if old == new and not force:
            revisions[die] = new
            continue
        diff = git(src, "diff", "--name-only", old, new) if old and not force else None
        hits = flow_paths(diff.stdout.split(), spec or {"watch": watch}, die) if diff and diff.returncode == 0 else ["(first / forced / diff unavailable)"]
        if "tools/flow_canary/canaries.json" in hits and spec:
            before = git(src, "show", old + ":tools/flow_canary/canaries.json")
            try:
                previous = json.loads(before.stdout) if before.returncode == 0 else None
            except ValueError:
                previous = None
            if isinstance(previous, dict) and not _watch_module.spec_flow_changed(previous, spec, die):
                hits.remove("tools/flow_canary/canaries.json")
        if hits:
            ready.append(die)
            hits_all.update(hits)
        else:
            revisions[die] = new
    return ready, revisions, sorted(hits_all)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--root", default="/srv/opentallas-scratch2/claude/flow-canary/runs")
    ap.add_argument("--state", default=str(STATE))
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    st = Path(a.state)
    state = json.loads(st.read_text()) if st.is_file() else {}
    if git(a.src, "fetch", "-q", "origin", "main").returncode:
        print("FLOW_CANARY_TRIGGER fetch failed")
        return 2
    released = unlock_completed_sources(a.src, a.root)
    if released:
        print(f"FLOW_CANARY_TRIGGER completed sources released for reaper: {released}")
    new = git(a.src, "rev-parse", "origin/main").stdout.strip()
    spec = json.loads((HERE / "canaries.json").read_text())
    specs = [c["die"] for c in spec["canaries"]]
    busy = live_dies(a.root)
    dies, revisions, hits = ready_dies(a.src, new, specs, spec["watch"], state, busy, a.force, spec=spec)
    print(f"FLOW_CANARY_TRIGGER main {new[:9]}: submit {dies}; existing live {sorted(busy)}; changes {hits[:8]}")
    if a.dry:
        return 0
    if dies:
        try:
            pinned_src = source_snapshot(a.src, new, a.root)
        except RuntimeError as e:
            print(f"FLOW_CANARY_TRIGGER source staging failed: {e}")
            return 2
        r = subprocess.run([sys.executable, "-I", str(HERE / "canary.py"), "submit",
                            "--src", str(pinned_src), "--root", a.root] + sum([["--die", d] for d in dies], []))
        if r.returncode:
            return r.returncode
        revisions.update({die: new for die in dies})
    state.update(die_sha=revisions, checked=time.strftime("%F %T %Z"), hits=hits[:20], dies=dies)
    if all(revisions.get(die) == new for die in specs):
        state["last_sha"] = new
    st.parent.mkdir(parents=True, exist_ok=True)
    st.write_text(json.dumps(state, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
