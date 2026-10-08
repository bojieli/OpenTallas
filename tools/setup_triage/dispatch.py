#!/usr/bin/env python3
"""Fan the setup-triage path dump out to the hosts that hold each route (4 concurrent per host)."""
import json, subprocess, sys, os, collections, shlex
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(sys.argv[1]))
only = set(sys.argv[2:])
BASE = "/tmp/setup-triage-claude"
def one(t):
    job, host, orfs = t["job"], t["host"], t["orfs"]
    if not orfs:
        return job, "no-orfs"
    run = orfs.split("/routes/")[0]
    out = f"{BASE}/{job}"
    cmd = (f"mkdir -p {out} {BASE}/bin && cat > {out}/paths_tcl.tcl && "
           f"bash {BASE}/bin/remote_paths.sh {shlex.quote(job)} {orfs} {run}/src {out}; tail -1 {out}/paths.log")
    r = subprocess.run(["ssh", host, cmd], input=open(f"{HERE}/paths_tcl.tcl").read(), capture_output=True, text=True, timeout=5400)
    os.makedirs(f"/tmp/setup-triage-local/{job}", exist_ok=True)
    subprocess.run(["scp", "-q", f"{host}:{out}/paths.log", f"{host}:{out}/sdc_all.txt", f"/tmp/setup-triage-local/{job}/"])
    return job, (r.stdout + r.stderr).strip()[-200:]
byhost = collections.defaultdict(list)
for t in T:
    if only and t["job"] not in only: continue
    byhost[t["host"]].append(t)
for h in byhost:
    subprocess.run(["ssh", h, f"mkdir -p {BASE}/bin"]); subprocess.run(["scp", "-q", f"{HERE}/remote_paths.sh", f"{h}:{BASE}/bin/"])
def host_run(h):
    with ThreadPoolExecutor(2 if h == "ot-epyc3" else 4) as ex:
        for job, res in ex.map(one, byhost[h]):
            print(h, job, res.replace("\n", " | "), flush=True)
with ThreadPoolExecutor(len(byhost)) as ex:
    list(ex.map(host_run, byhost))
