#!/usr/bin/env python3
# REFILL-0325/MRGBENCH: run kit job.json stages.bench on a merge-tree snapshot, closure-daemon verdict semantics
import json, os, re, subprocess, sys, concurrent.futures as cf
src, out, par, kits = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:]
env = dict(os.environ); env["PATH"] = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin") + ":" + env["PATH"]
ERR = re.compile(r"readmem.*(file\s+not\s+found|unable.*open|cannot.*open|could\s+not.*open|no\s+such\s+file)", re.I)
def run(a):
    kit, st = a
    rd = os.path.join(out, kit, st["name"]); os.makedirs(rd, exist_ok=True)
    cmd = st["cmd"].replace("{RUN}/src", "{SRC}").replace("{RUN}", rd).replace("{SRC}", src)
    lg = os.path.join(out, kit, st["name"] + ".log")
    with open(lg, "w") as f:
        rc = subprocess.run(["bash", "-o", "pipefail", "-c", cmd], cwd=src, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    full = open(lg, errors="replace").read(); inerr = bool(ERR.search(full))
    if st["expect"] == "pass":
        ok = rc == 0 and not inerr and (not st.get("pass_regex") or re.search(st["pass_regex"], full, re.M) is not None)
    else:
        seen = (re.search(st["fail_regex"], full, re.M) is not None) if st.get("fail_regex") else (rc != 0 or re.search(r"^FAIL\b", full, re.M) is not None)
        ok = seen and not inerr
    return dict(kit=kit, name=st["name"], expect=st["expect"], rc=rc, ok=ok, input_error=inerr)
work = []
for k in kits:
    os.makedirs(os.path.join(out, k), exist_ok=True)
    work += [(k, s) for s in json.load(open(os.path.join(src, "physical/ref_tile", k, "job.json")))["stages"]["bench"]]
with cf.ThreadPoolExecutor(par) as ex: res = list(ex.map(run, work))
v = subprocess.run([env["PATH"].split(":")[0] + "/verilator", "--version"], capture_output=True, text=True).stdout.strip()
for k in kits:
    r = [x for x in res if x["kit"] == k]
    json.dump(dict(kit=k, verilator=v, results=r, unexpected=sum(not x["ok"] for x in r)), open(os.path.join(out, k, "summary.json"), "w"), indent=1)
for r in res: print(("OK  " if r["ok"] else "BAD ") + f"{r['kit']} {r['name']} expect={r['expect']} rc={r['rc']}")
for k in kits:
    r = [x for x in res if x["kit"] == k]
    print(f"MRGBENCH {k}: {sum(x['expect']=='pass' for x in r)} pass / {sum(x['expect']!='pass' for x in r)} mutants, {sum(not x['ok'] for x in r)} unexpected ({v})")
