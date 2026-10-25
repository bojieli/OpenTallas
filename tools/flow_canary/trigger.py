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
    last = state.get("last_sha")
    if new == last and not a.force:
        print(f"FLOW_CANARY_TRIGGER idle main {new[:9]}")
        return 0
    spec = json.loads((HERE / "canaries.json").read_text())
    if last and not a.force:
        diff = git(a.src, "diff", "--name-only", last, new)
        hits = touched(diff.stdout.split(), spec["watch"]) if diff.returncode == 0 else ["(diff failed)"]
    else:
        hits = ["(first run / --force)"]
    if not hits:
        print(f"FLOW_CANARY_TRIGGER main {last[:9]}..{new[:9]}: no flow-tool change")
        state.update(last_sha=new, checked=time.strftime("%F %T %Z"))
    else:
        busy = live_dies(a.root)
        dies = [c["die"] for c in spec["canaries"] if c["die"] not in busy]
        print(f"FLOW_CANARY_TRIGGER main {new[:9]}: flow tools changed {hits[:8]}; submit {dies} (still running: "
              f"{sorted(busy)})")
        if a.dry:
            return 0
        if git(a.src, "checkout", "-q", "--detach", new).returncode:
            print("FLOW_CANARY_TRIGGER checkout failed")
            return 2
        if dies:
            r = subprocess.run([sys.executable, "-I", str(Path(a.src) / "tools/flow_canary/canary.py"), "submit",
                                "--src", a.src, "--root", a.root] + sum([["--die", d] for d in dies], []))
            if r.returncode:
                return r.returncode
        state.update(last_sha=new, submitted=time.strftime("%F %T %Z"), hits=hits[:20], dies=dies)
    st.parent.mkdir(parents=True, exist_ok=True)
    st.write_text(json.dumps(state, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
