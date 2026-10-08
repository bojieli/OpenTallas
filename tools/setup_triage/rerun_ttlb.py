#!/usr/bin/env python3
"""Re-run only the TT + link-budget STA of every tt_restatus job with the current link_budget_consistent.sdc."""
import json, subprocess, sys, os, collections
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T = json.load(open(sys.argv[1])); SDC = open(f"{ROOT}/physical/common_flow/link_budget_consistent.sdc").read()
TT2 = {"core_kv_banked_fullwidth_d9d511777", "core_p_done_io80-751b7b4d4", "core_separate_load_fullwidth_fbc523a6f"}
def one(t):
    job, host, orfs = t["job"], t["host"], t["orfs"]
    out = f"/tmp/setup-triage-claude/{'tt2' if job in TT2 else 'tt'}/{job}"
    src = f"{out}/src"
    cmd = (f"cat > {out}/link_budget_consistent.sdc && timeout 5400 docker run --rm -v {orfs}:/work:ro -v {src}:/src:ro -v {out}:/tri "
           f"openroad/orfs:asap7lock bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /tri/ttlb.tcl' > {out}/ttlb.log 2>&1; "
           f"echo TRI_RC $? >> {out}/ttlb.log; grep -E '^OT_WS |TRI_RC|async_pins' {out}/ttlb.log | tr '\\n' ' '")
    c = ["bash", "-c", cmd] if host == "localhost" else ["ssh", host, cmd]
    r = subprocess.run(c, input=SDC, capture_output=True, text=True)
    src_log = f"{out}/ttlb.log"
    if host == "localhost": subprocess.run(["cp", src_log, f"/tmp/setup-triage-local/tt/{job}/ttlb.log"])
    else: subprocess.run(["scp", "-q", f"{host}:{src_log}", f"/tmp/setup-triage-local/tt/{job}/ttlb.log"])
    return job, r.stdout.strip()[-200:]
by = collections.defaultdict(list)
for t in T: by[t["host"]].append(t)
def hr(h):
    with ThreadPoolExecutor({"localhost": 1, "ot-epyc3": 3, "ot-pve1": 2, "ot-agidock128": 4}.get(h, 8)) as ex:
        for job, res in ex.map(one, by[h]): print(h, job, res, flush=True)
with ThreadPoolExecutor(len(by)) as ex: list(ex.map(hr, by))
