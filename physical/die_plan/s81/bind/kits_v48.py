#!/usr/bin/env python3
"""ELEM-S81 bind48 10-24: kit-rtl + gen.py phys (G3 kit gen with sdc_lint) for the S81 v4.8 non-frame types that need
a bind (ELEM-S81 list), on the r8 bind RUN/b48r8.  A type that split (bind_report type_splits) is kitted per variant
(T, T__v1, ...; each variant's gen.py phys goes to its own KITS[_vN] dir since the plan type name is the same).
Usage: kits_v48.py RUN WT KITS TYPE...   -> RUN/kits_v48_summary.json"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

run, wt, kits = sys.argv[1:4]
types = sys.argv[4:]
P = f"{wt}/physical/die_plan/s81/die_plan.json"
O = f"{run}/b48r8"
AB = f"{run}/asbuilt_v48_r8.json"
rep = json.load(open(f"{O}/bind_report.json"))
spl = {t["type"]: t["variants"] for t in rep["type_splits"]}
jobs = []
for t in types:
    for k in range(len(spl.get(t, [None]))):
        jobs.append((t, f"{t}__v{k}" if k else None, k))


def last_json(s):
    for ln in reversed(s.strip().splitlines()):
        try:
            return json.loads(ln)
        except Exception:
            continue
    return s.strip().splitlines()[-1][:400] if s.strip() else ""


def one(j):
    t, v, k = j
    kd = f"{O}/kit_rtl/{v or t}"
    cmd = ["python3", f"{wt}/tools/die_plan/bind.py", "kit-rtl", P, "--out", O, "--type", t, "--kit", kd, "--asbuilt", AB]
    if v:
        cmd += ["--variant", v]
    p = subprocess.run(cmd, capture_output=True, text=True)
    r = dict(name=v or t, type=t, variant=v, instances=spl.get(t, [[None]])[k] if t in spl else None,
             kit_rtl_rc=p.returncode, kit_rtl=last_json(p.stdout + p.stderr), kit_rtl_dir=kd)
    if p.returncode != 0:
        r["kit_rtl_err"] = (p.stdout + p.stderr)[-1500:]
        return r
    out = kits if not k else f"{kits}_v{k}"
    g = subprocess.run(["python3", f"{wt}/tools/die_plan/gen.py", "phys", P, "--out", out, "--types", t,
                        "--kit-rtl", f"{t}={kd}/kit_rtl.f"], capture_output=True, text=True, cwd=wt)
    r.update(gen_rc=g.returncode, gen_out=out, gen_tail=(g.stdout + g.stderr)[-1200:])
    return r


res = list(ThreadPoolExecutor(8).map(one, jobs))
json.dump(res, open(f"{run}/kits_v48_summary.json", "w"), indent=1)
for r in res:
    print(r["name"], "kit_rtl", r["kit_rtl_rc"], "gen", r.get("gen_rc"),
          {k: v for k, v in r["kit_rtl"].items() if not isinstance(v, (list, dict))} if isinstance(r["kit_rtl"], dict) else r["kit_rtl"])
