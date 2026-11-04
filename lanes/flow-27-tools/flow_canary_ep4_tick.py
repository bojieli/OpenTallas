#!/usr/bin/python3 -I
"""FLOW-27 11-04: automatic flow canaries on epyc4, driven from intel2 (replaces flow-canary.timer, which wrote to intel2).
Every 15 min (flow-canary-ep4.timer): newest flow tag of each die; same flow-diff rule and one-run-per-die as trigger.py, so a
busy die goes straight to the newest tag when it frees.  Verdicts are posted to the queue.  COORD 05:36 (3), 06:0x.
A REGRESSION here does not hold rows (canary_gate reads the intel2 root only): the posted line is what acts."""
import json, os, re, subprocess, sys, time
from pathlib import Path
REPO = "/home/ubuntu/OpenTallas"
sys.path.insert(0, REPO + "/tools/flow_canary")
import trigger
HOME = Path.home()
STATE = HOME / ".local/state/flow_canary/ep4_state.json"
TOOL = HOME / ".local/share/flow_canary"
EP4_TOOL = "/srv/opentallas-scratch3/claude/flow-canary/tool"
TAG = {"s81": "s81", "s81_cl": "s81", "s81_head": "head", "s81_head_cl": "head", "qwen_compute": "qc",
       "qwen_kvsys": "kv", "qwen_kvsys_core": "kv", "hbm": "hbm", "hbm_sram": "hbm"}
SSH = ["ssh", "-n", "-o", "ControlPath=none", "-o", "ConnectTimeout=30", "epyc4"]
def sh(*a, timeout=600):
    return subprocess.run(a, capture_output=True, text=True, timeout=timeout)
def unit(die):
    return "flow-canary-ep4-" + die.replace("_", "-")
def active(u):
    return sh("systemctl", "--user", "is-active", u).stdout.strip() in ("active", "activating", "deactivating")
def newest_tags():
    out = sh("git", "-C", REPO, "for-each-ref", "--sort=creatordate", "--format=%(refname:short) %(*objectname) %(objectname)", "refs/tags/flow-*").stdout
    tags = {}
    for line in out.splitlines():
        f = line.split()
        m = re.search(r"-(s81|head|qc|kv|hbm)$", f[0])
        if m:
            tags[m.group(1)] = (f[0], f[1])          # %(*objectname) is the peeled commit of an annotated tag
    return tags
def post(lines):
    q = HOME / "coord/lanes/COORD-REVIEW-QUEUE.md"
    stamp = time.strftime("%F %H:%M %Z")
    with q.open("a") as f:
        for l in lines:
            f.write(f"- {stamp} RESULT [FLOW-CANARY-EP4 -> COORD, ROOT-MERGE] {l}\n")
    r = sh("timeout", "280", str(HOME / "coord/bin/coord-commit.sh"), "flow canary epyc4 verdicts", "lanes/COORD-REVIEW-QUEUE.md", timeout=300)
    print("post rc", r.returncode, r.stdout[-200:], r.stderr[-200:])
    return r.returncode == 0
def main():
    state = json.loads(STATE.read_text()) if STATE.is_file() else {}
    if sh("git", "-C", REPO, "fetch", "-q", "origin", "main", "+refs/tags/flow-*:refs/tags/flow-*").returncode:
        print("fetch failed"); return 2
    spec = json.loads(Path(REPO, "tools/flow_canary/canaries.json").read_text())
    specs = [c["die"] for c in spec["canaries"]]
    # verdicts first
    r = sh(*SSH, f"python3 -I {EP4_TOOL}/ep4_state.py --prune", timeout=900)
    if r.returncode:
        print("epyc4 unreachable or state failed:", r.stderr[-300:]); return 2
    posted = set(state.get("posted", []))
    lines, new_posted = [], []
    for raw in r.stdout.splitlines():
        v = json.loads(raw)
        if v["run"] in posted:
            continue
        new_posted.append(v["run"])
        lines.append(f"{v['die']} @ {str(v['src'])[:11]}: {v['verdict']} (absolute {v['canary']}), {v['run']}"
                     + (f". {v['why']}" if v["verdict"] != "NO-REGRESSION" else "") + " [CHECKED canary.json; automatic]")
    if lines and post(lines):
        state["posted"] = sorted(posted | set(new_posted))
    # newest tag per die
    tags = newest_tags()
    revisions = dict(state.get("die_sha", {}))
    busy = {d for d in specs if active(unit(d)) or active("flow27-e-" + d.replace("_", "-"))}
    todo = {}
    for die in specs:
        t = tags.get(TAG[die])
        if not t:
            continue
        ready, revs, hits = trigger.ready_dies(REPO, t[1], [die], spec["watch"], dict(die_sha=revisions), busy, False, spec=spec)
        revisions[die] = revs.get(die, revisions.get(die))
        if ready:
            todo.setdefault(t[1], []).append(die)
    print(time.strftime("%F %T"), "todo", todo, "busy", sorted(busy))
    for sha, dies in todo.items():
        r = sh(*SSH, f"bash {EP4_TOOL}/canary_tag_epyc4.sh {sha} " + " ".join(dies), timeout=1200)
        print(r.stdout[-800:], r.stderr[-400:])
        for line in r.stdout.splitlines():
            f = line.split("\t")
            if f[0] != "RUN":
                continue
            _, die, run, mem, th, src = f
            log = TOOL / "logs" / (Path(run).name + ".log")
            log.parent.mkdir(parents=True, exist_ok=True)
            c = subprocess.run(["systemd-run", "--user", "--unit", unit(die), "--collect", "--property=Type=exec",
                                "--property=KillMode=process", "--", "bash", "-lc",
                                f"{TOOL}/canary_drive_epyc4.sh {run} {mem} {th} {src} > {log} 2>&1"], capture_output=True, text=True)
            if c.returncode == 0:
                revisions[die] = sha
            print("launch", die, run, c.returncode, c.stderr[-200:])
    state.update(die_sha=revisions, checked=time.strftime("%F %T %Z"))
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1) + "\n")
    return 0
if __name__ == "__main__":
    sys.exit(main())
