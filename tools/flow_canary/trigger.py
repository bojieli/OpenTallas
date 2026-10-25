#!/usr/bin/env python3
"""flow_canary trigger: submit the die canaries when main changes a flow tool (systemd user timer on epyc1).

    trigger.py --src /srv/opentallas-scratch2/claude/wt/flow-canary [--root RUNS] [--state FILE] [--dry] [--force]

Fetches origin/main into the canary worktree (a detached, sparse checkout owned by FLOW-CANARY), and when any commit
since the last canaried main touches a path in canaries.json "watch", checks the worktree out at the new main and runs
`canary.py submit` for every die whose previous canary is not still running.  State: last canaried sha + per-die run.
"""
import argparse
import fnmatch
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE = Path.home() / ".local/state/flow_canary/state.json"
LIVE_S = 12 * 3600


def git(src, *a):
    return subprocess.run(["git", "-C", str(src), *a], text=True, capture_output=True)


def touched(paths, watch):
    return sorted({p for p in paths for w in watch if fnmatch.fnmatch(p, w)})


def live_dies(root, now=None):
    """dies with a run dir younger than LIVE_S that has no canary.json yet"""
    now = now or time.time()
    out = set()
    for d in glob.glob(f"{root}/*/canary_meta.json"):
        run = Path(d).parent
        if not (run / "canary.json").exists() and now - run.stat().st_mtime < LIVE_S:
            m = json.loads(Path(d).read_text())
            out.add(m["spec"]["die"])
    return out


def source_snapshot(src, sha, root):
    """An immutable sparse source per revision; no checkout underneath any live canary."""
    dest = Path(root).parent / "sources" / sha[:12]
    if dest.exists():
        head = git(dest, "rev-parse", "HEAD")
        if head.returncode or head.stdout.strip() != sha:
            raise RuntimeError(f"canary source snapshot {dest} is not pinned to {sha}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = git(src, "worktree", "add", "--no-checkout", "--detach", str(dest), sha)
    if r.returncode:
        raise RuntimeError(r.stderr)
    patterns = "/*\n!/results/\n!/docs/\n!/.qscratch/\n!/physical/\n/physical/die_plan/\n/physical/common_flow/\n/physical/ref_tile/\n!/physical/ref_tile/*/\n!/physical/die_plan/*/cores/harden/results/\n"
    r = subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", "--no-cone", "--stdin"],
                       input=patterns, text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    r = git(dest, "checkout", "--detach", sha)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return dest


def ready_dies(src, new, specs, watch, state, busy, force=False):
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
        hits = touched(diff.stdout.split(), watch) if diff and diff.returncode == 0 else ["(first / forced / diff unavailable)"]
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
    new = git(a.src, "rev-parse", "origin/main").stdout.strip()
    spec = json.loads((HERE / "canaries.json").read_text())
    specs = [c["die"] for c in spec["canaries"]]
    busy = live_dies(a.root)
    dies, revisions, hits = ready_dies(a.src, new, specs, spec["watch"], state, busy, a.force)
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
