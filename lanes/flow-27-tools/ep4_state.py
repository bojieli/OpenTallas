#!/usr/bin/python3 -I
"""FLOW-27 11-04: run ON epyc4 by the tick.  Prints finished canary verdicts as JSON lines; with --prune also removes
finished NO-REGRESSION runs older than 48 h and source snapshots no run has used for 48 h.
Never removes REGRESSION/unfinished runs, baselines, a run holding a SIGNED signoff.json or .keep, or anything live."""
import glob, json, os, shutil, subprocess, sys, time
ROOT = "/srv/opentallas-scratch3/claude/flow-canary"
RUNS = ROOT + "/runs"
now = time.time()
newest_use = {}
for meta in glob.glob(RUNS + "/*/canary_meta.json"):
    run = os.path.dirname(meta)
    src = json.load(open(meta)).get("src", "")
    newest_use[src] = max(newest_use.get(src, 0), os.path.getmtime(meta))
    try:
        c = json.load(open(run + "/canary.json"))
    except (OSError, ValueError):
        continue
    reg = c.get("regression") or {}
    verdict = reg.get("verdict") if isinstance(reg, dict) else None
    print(json.dumps(dict(run=run, die=c.get("die"), src=c.get("src"), verdict=verdict, canary=c.get("verdict"), why=str((reg or {}).get("why", ""))[:300])))
    if "--prune" in sys.argv and verdict == "NO-REGRESSION" and now - os.path.getmtime(run + "/canary.json") > 48 * 3600:
        signed = os.path.exists(run + "/.keep") or subprocess.run(
            ["grep", "-rl", "--include=signoff.json", '"SIGNED"', run], capture_output=True, text=True).stdout.strip()
        if not signed:
            shutil.rmtree(run, ignore_errors=True)
if "--prune" in sys.argv:
    live = subprocess.run("ps -eo cmd", shell=True, capture_output=True, text=True).stdout
    for src in glob.glob(ROOT + "/sources/*"):
        if src in live or now - max(newest_use.get(src, 0), os.path.getmtime(src)) < 48 * 3600:
            continue
        subprocess.run(["git", "-C", "/home/ubuntu/OpenTallas", "worktree", "remove", "-f", "-f", src], capture_output=True)
