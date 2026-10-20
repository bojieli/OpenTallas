#!/usr/bin/env python3
# REFILL-1830/MRGBENCH: run a kit job.json's stages.bench on a merge-tree snapshot, closure-daemon verdict semantics
import json, os, re, subprocess, sys, concurrent.futures as cf
src, job, out, par = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
j = json.load(open(job)); bs = j["stages"]["bench"]
os.makedirs(out, exist_ok=True)
env = dict(os.environ); env["PATH"] = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin") + ":" + env["PATH"]
ERR = re.compile(r"readmem.*(file\s+not\s+found|unable.*open|cannot.*open|could\s+not.*open|no\s+such\s+file)", re.I)
def run(st):
    rd = os.path.join(out, st["name"]); os.makedirs(rd, exist_ok=True)
    cmd = st["cmd"].replace("{RUN}/src", "{SRC}").replace("{RUN}", rd).replace("{SRC}", src)
    lg = os.path.join(out, st["name"] + ".log")
    with open(lg, "w") as f:
        rc = subprocess.run(["bash", "-o", "pipefail", "-c", cmd], cwd=src, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    full = open(lg, errors="replace").read()
    inerr = bool(ERR.search(full))
    if st["expect"] == "pass":
        ok = rc == 0 and not inerr and (not st.get("pass_regex") or re.search(st["pass_regex"], full, re.M) is not None)
    else:
        seen = (re.search(st["fail_regex"], full, re.M) is not None) if st.get("fail_regex") else (rc != 0 or re.search(r"^FAIL\b", full, re.M) is not None)
        ok = seen and not inerr
    return dict(name=st["name"], expect=st["expect"], rc=rc, ok=ok, input_error=inerr)
with cf.ThreadPoolExecutor(par) as ex:
    res = list(ex.map(run, bs))
v = subprocess.run([env["PATH"].split(":")[0] + "/verilator", "--version"], capture_output=True, text=True).stdout.strip()
json.dump(dict(job=job, verilator=v, results=res, unexpected=sum(not r["ok"] for r in res)), open(os.path.join(out, "summary.json"), "w"), indent=1)
for r in res: print(("OK  " if r["ok"] else "BAD ") + f"{r['name']} expect={r['expect']} rc={r['rc']}")
print(f"MRGBENCH {os.path.basename(os.path.dirname(job))}: {len(res)} stages, {sum(not r['ok'] for r in res)} unexpected ({v})")
