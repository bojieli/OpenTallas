#!/usr/bin/env python3
import json, subprocess, sys, os, collections
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(sys.argv[1]))
def one(t):
    job, host, orfs = t["job"], t["host"], t["orfs"]
    base = f"/tmp/setup-triage-claude/tt/{job}"; out = f"/tmp/setup-triage-claude/ss_{job}"
    subprocess.run(["ssh", host, f"mkdir -p {out}"])
    subprocess.run(["scp", "-q", f"{HERE}/srcsync.py", f"{HERE}/remote_srcsync.sh", f"{host}:{out}/"])
    r = subprocess.run(["ssh", host, f"bash {out}/remote_srcsync.sh {job} {orfs} {base}/src {out}"], capture_output=True, text=True)
    os.makedirs(f"/tmp/setup-triage-local/srcsync/{job}", exist_ok=True)
    subprocess.run(["scp", "-q", f"{host}:{out}/p1.log", f"{host}:{out}/p2.log", f"{host}:{out}/pmap.json", f"{host}:{out}/srcsync.sdc", f"/tmp/setup-triage-local/srcsync/{job}/"])
    return job, (r.stdout + r.stderr).strip().replace("\n", " | ")[-400:]
by = collections.defaultdict(list)
for t in T: by[t["host"]].append(t)
def hr(h):
    with ThreadPoolExecutor(3) as ex:
        for j, r in ex.map(one, by[h]): print(h, j, r, flush=True)
with ThreadPoolExecutor(len(by)) as ex: list(ex.map(hr, by))
