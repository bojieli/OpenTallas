#!/usr/bin/env python3
"""MULTI-VT (owner 2026-10-07): build the <job>-tt-lvt closure-loop job for a block whose TT miss closes with <= ~2 %
LVT cells (tools/multivt/summarize.py policy).

Source = the base job's own commit (its RTL / physical recipe unchanged) + ONE overlay commit carrying the current main
flow files (run_abi3_physical with OT_MULTI_VT and option-B OT_ORFS_CORNER, orfs_hold_mm, corner_sta / export with
VT-library detection), pushed as claude/multivt-20261007-<job9>.  The job routes with OT_MULTI_VT=lvt, mm hold
(route_hold_corners mm, the base job's OT_MM_FF_SDC / verdict post-SDCs), TC primary corner (the loop's option-B export).

    make_lvt_job.py <base job> [--flow-ref origin/main] [--drop]     # --drop: copy into the loop's job dir
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

JOBS = Path.home() / ".local/state/closure_loop/jobs"
DROP = Path("/tmp/claude-review-20261003/closure_jobs")
OUTDIR = Path("/home/ubuntu/claude-takeover-20261007/multivt-jobs")
REPO = Path("/home/ubuntu/OpenTallas")
FLOW = ["tools/run_abi3_physical.py", "tools/orfs_hold_mm.py", "tools/orfs_hold_mm.tcl", "tools/orfs_allcorner_spef.py",
        "tools/w18/corner_sta.py", "tools/w18/corner_sta_ref.py", "tools/w18/export_view.py",
        "tools/hbm_fmax_attn_abstract.py", "tools/multivt/vt_swap_sta.py"]


def git(*a, cwd=REPO, check=True):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=check).stdout.strip()


def overlay_branch(commit, tag, flow_ref):
    br = f"claude/multivt-20261007-{tag}"
    with tempfile.TemporaryDirectory(prefix="mvt-ov-") as td:
        wt = Path(td) / "wt"
        git("worktree", "add", "-q", "--detach", str(wt), commit)
        try:
            present = [f for f in FLOW
                       if subprocess.run(["git", "cat-file", "-e", f"{flow_ref}:{f}"], cwd=REPO).returncode == 0]
            git("checkout", flow_ref, "--", *present, cwd=wt)
            if git("status", "--porcelain", cwd=wt):
                git("commit", "-q", "-m", f"multivt overlay: current flow files from {flow_ref} "
                    f"({git('rev-parse', '--short=9', flow_ref)}) on {commit[:9]} for an OT_MULTI_VT=lvt route\n\n"
                    "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
                    "Claude-Session: https://claude.ai/code/session_01NV6PW3KgjHmYWi8wwSxoFF", cwd=wt)
            head = git("rev-parse", "HEAD", cwd=wt)
            git("push", "-q", "-f", "origin", f"{head}:refs/heads/{br}", cwd=wt)
        finally:
            git("worktree", "remove", "--force", str(wt), check=False)
    return br, head


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--flow-ref", default="origin/claude/multivt-20261007")
    ap.add_argument("--drop", action="store_true")
    a = ap.parse_args()
    git("fetch", "-q", "origin")
    j = json.loads((JOBS / f"{a.job}.json").read_text())["spec"]
    s = json.loads(json.dumps(j))
    br, head = overlay_branch(j["source"]["commit"], re.sub(r"[^A-Za-z0-9]", "", a.job)[-24:], a.flow_ref)
    s["name"] = f"{a.job}-tt-lvt"
    s["owner"] = "Claude:multivt"
    s["purpose"] = (f"OT_MULTI_VT=lvt re-route of {a.job} (owner 2026-10-07: RVT default, LVT <= ~2% cells on small TT "
                    "misses); same RTL/recipe, TC route + mm hold; " + (j.get("purpose") or "")[:300])
    s["source"] = {**j["source"], "branch": br, "commit": head}
    post = " ".join(s.get("verdict", {}).get("post_sdc", []))
    for st in ("calibrate", "route"):
        c = s["stages"].get(st) or {}
        if c.get("cmd"):
            pre = "export OT_MULTI_VT=lvt; "
            if "OT_MM_FF_SDC" not in c["cmd"] and post:
                pre += f"export OT_MM_FF_SDC='{post}'; "
            c["cmd"] = pre + c["cmd"]
    s["route_hold_corners"] = "mm"
    s.setdefault("route_hold_margin_ns", 0.05)
    s["merge_target"] = None
    for r in s.get("record", []):
        r["to"] = f"physical/multivt/{s['name']}/" + Path(r["to"]).name
    OUTDIR.mkdir(parents=True, exist_ok=True)
    p = OUTDIR / f"{s['name']}.json"
    p.write_text(json.dumps(s, indent=1) + "\n")
    print(p, br, head[:9])
    if a.drop:
        (DROP / p.name).write_text(p.read_text())
        print("dropped", DROP / p.name)


if __name__ == "__main__":
    main()
