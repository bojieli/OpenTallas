#!/usr/bin/env python3
"""MULTI-VT (2026-10-07): launch tools/multivt/vt_swap_sta.py on the host of each named closure-loop job, against the
route its verdict was taken from (spec.verdict.corner_sta -> corner_sta.json -> orfs_dir).  Detached (nohup), outputs
under <host scratch root>/claude/multivt/<job>/ (never inside the job's run dir).

    dispatch_resta.py launch <job> [<job> ...]      # resolve + copy the tool + start
    dispatch_resta.py collect <job> [...] > all.json
    OT_VT_CORNER=tt dispatch_resta.py launch|collect ...   # TT setup search (owner option B), outputs <job>-tt/
"""
import json
import subprocess
import sys
from pathlib import Path

JOBS = Path.home() / ".local/state/closure_loop/jobs"
TOOL = Path(__file__).resolve().parent / "vt_swap_sta.py"


def sh(host, cmd, **kw):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", host, cmd], capture_output=True, text=True, **kw)


def resolve(name):
    j = json.loads((JOBS / f"{name}.json").read_text())
    s, run, host = j["spec"], j["run"], j["host"]
    cs = s["verdict"]["corner_sta"].replace("{RUN}", run).replace("{NAME}", s["name"])
    orfs = (j.get("metrics") or {}).get("orfs_dir") or ""
    if not orfs:
        r = sh(host, f"python3 -c \"import json,glob;f=sorted(glob.glob('{cs}'))[-1];print(json.load(open(f))['orfs_dir'])\"")
        orfs = r.stdout.strip()
    root = run.rsplit("/claude/closure-loop/", 1)[0]
    return dict(name=name, host=host, run=run, orfs=orfs, src=f"{run}/src", out=f"{root}/claude/multivt/{name}",
                bin=f"{root}/claude/multivt/bin", metrics=j.get("metrics"))


def launch(names, extra=""):
    for n in names:
        r = resolve(n)
        if TAG:
            r["out"] += TAG
        if not r["orfs"]:
            print(n, "UNRESOLVED", file=sys.stderr)
            continue
        sh(r["host"], f"mkdir -p {r['bin']} {r['out']}")
        subprocess.run(["scp", "-q", str(TOOL), f"{r['host']}:{r['bin']}/vt_swap_sta.py"], check=True)
        subprocess.run(["ssh", "-f", "-n", r["host"], f"cd /tmp && setsid nohup python3 {r['bin']}/vt_swap_sta.py --orfs-dir {r['orfs']} --src {r['src']} "
                      f"--out {r['out']} {extra} > {r['out']}/driver.log 2>&1 < /dev/null &"], check=False)
        print(json.dumps(r))


def collect(names):
    out = {}
    for n in names:
        r = resolve(n)
        if TAG:
            r["out"] += TAG
        p = sh(r["host"], f"cat {r['out']}/vt_swap_sta.json 2>/dev/null")
        out[n] = dict(**r, result=json.loads(p.stdout) if p.stdout.strip() else None)
    print(json.dumps(out, indent=1))


import os  # noqa: E402
TAG = "-tt" if os.environ.get("OT_VT_CORNER") == "tt" else ""

if __name__ == "__main__":
    if sys.argv[1] == "launch":
        launch(sys.argv[2:], "--setup-corner tt" if TAG else "")
    else:
        collect(sys.argv[2:])
