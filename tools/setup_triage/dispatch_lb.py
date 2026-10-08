#!/usr/bin/env python3
import json, subprocess, sys, os, collections, shlex
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
T = json.load(open(sys.argv[1])); BASE = "/tmp/setup-triage-claude"
def one(t):
    job, host, orfs = t["job"], t["host"], t["orfs"]
    run = orfs.split(f"/{job}/")[0] + f"/{job}"; out = f"{BASE}/lb/{job}"
    # the run's src snapshot may be pruned after CLOSED: rebuild the /src files the STA reads from the job's commit
    commit = json.load(open(os.path.expanduser(f"~/.local/state/closure_loop/jobs/{job}.json")))["spec"]["source"]["commit"]
    rd = (lambda c: subprocess.run(["bash", "-c", c], capture_output=True, text=True).stdout) if host == "localhost" else \
         (lambda c: subprocess.run(["ssh", host, c], capture_output=True, text=True).stdout)
    paths = sorted(set(x[5:] for x in rd(f"grep -o '/src/[^ ]*' {orfs}/w18_sta_ss.tcl").split() if x.startswith("/src/")))
    srcd = f"{out}/src"
    run_cmd = (lambda c: subprocess.run(["bash", "-c", c], capture_output=True, text=True)) if host == "localhost" else \
              (lambda c: subprocess.run(["ssh", host, c], capture_output=True, text=True))
    missing = []
    for pth in paths:   # prefer the run's own snapshot (it holds generated SDCs), else the commit, else the run's cl/
        r = run_cmd(f"mkdir -p {srcd}/$(dirname {pth}) && if [ -e {run}/src/{pth} ]; then cp -r {run}/src/{pth} {srcd}/{pth}; echo ok; fi")
        if "ok" in r.stdout: continue
        tar = subprocess.run(["git", "-C", ROOT, "archive", commit, pth], capture_output=True).stdout
        if tar:
            put = ["bash", "-c", f"tar xf - -C {srcd}"] if host == "localhost" else ["ssh", host, f"tar xf - -C {srcd}"]
            subprocess.run(put, input=tar); continue
        r = run_cmd(f"f={run}/cl/$(basename {pth}); [ -e $f ] && cp $f {srcd}/{pth} && echo ok")
        if "ok" not in r.stdout: missing.append(pth)
    if missing: print(job, "MISSING", missing, flush=True)
    cmd = (f"mkdir -p {out} && cat > {out}/link_budget_consistent.sdc && bash {BASE}/bin/remote_linkbudget.sh {shlex.quote(job)} {orfs} {srcd} {out}")
    if host == "localhost":
        r = subprocess.run(["bash", "-c", cmd], input=open(f"{ROOT}/physical/common_flow/link_budget_consistent.sdc").read(), capture_output=True, text=True)
    else:
        r = subprocess.run(["ssh", host, cmd], input=open(f"{ROOT}/physical/common_flow/link_budget_consistent.sdc").read(), capture_output=True, text=True, timeout=5400)
    os.makedirs(f"/tmp/setup-triage-local/lb/{job}", exist_ok=True)
    if host == "localhost": subprocess.run(["cp", f"{out}/lb.log", f"/tmp/setup-triage-local/lb/{job}/"])
    else: subprocess.run(["scp", "-q", f"{host}:{out}/lb.log", f"/tmp/setup-triage-local/lb/{job}/"])
    return job, (r.stdout + r.stderr).strip().replace("\n", " | ")
by = collections.defaultdict(list)
for t in T: by[t["host"]].append(t)
for h in by:
    if h == "localhost": os.makedirs(f"{BASE}/bin", exist_ok=True); subprocess.run(["cp", f"{HERE}/remote_linkbudget.sh", f"{BASE}/bin/"]); continue
    subprocess.run(["ssh", h, f"mkdir -p {BASE}/bin"]); subprocess.run(["scp", "-q", f"{HERE}/remote_linkbudget.sh", f"{h}:{BASE}/bin/"])
def hr(h):
    with ThreadPoolExecutor(1 if h in ("localhost", "ot-epyc3") else 3) as ex:
        for job, res in ex.map(one, by[h]): print(h, job, res, flush=True)
with ThreadPoolExecutor(len(by)) as ex: list(ex.map(hr, by))
