#!/usr/bin/env python3
"""PART-CAP: collect one capacity route (run on the host that ran it).

Per ORFS step log: wall s, CPU s (user+sys), CPU% (= mean threads busy x 100), peak RSS GB.  Plus instance counts
(synth / placed / final std cells), GPL/DPL/CTS/GRT/DRT outcomes, GRT overflow, DRC count, setup/hold WNS (ORFS
metrics at each stage; corner_sta.json TT/SS/FF sign-off when present), flow_rc and the 30-s container samples.
usage: collect.py RUN_DIR > summary.json"""
import glob, json, os, re, sys

d = sys.argv[1]
orfs = os.path.join(d, "work/orfs")
logs = sorted(glob.glob(f"{orfs}/logs/asap7/*/base/*.log"))
pat = re.compile(r"Elapsed time: (?:(\d+):)?(\d+):([\d.]+)\[h:\]min:sec\. CPU time: user ([\d.]+) sys ([\d.]+) "
                 r"\((\d+)%\)\. Peak memory: (\d+)KB")
steps = []
for lg in logs:
    txt = open(lg, errors="replace").read()
    for m in pat.finditer(txt):
        h, mi, s = int(m.group(1) or 0), int(m.group(2)), float(m.group(3))
        wall = h * 3600 + mi * 60 + s
        cpu = float(m.group(4)) + float(m.group(5))
        steps.append({"step": os.path.basename(lg)[:-4], "wall_s": round(wall, 1), "cpu_s": round(cpu, 1),
                      "threads_avg": round(cpu / wall, 2) if wall else None, "peak_rss_gb": round(int(m.group(7)) / 2**20, 2)})
    errs = sorted(set(re.findall(r"\[(?:ERROR|WARNING) (GPL-0\d+|DPL-0\d+|GRT-0\d+|DRT-0\d+|RSZ-0\d+|CTS-0\d+)\]", txt)))
    if steps and steps[-1]["step"] == os.path.basename(lg)[:-4]:
        steps[-1]["msgs"] = errs[:20]
out = {"run": os.path.basename(d.rstrip("/")), "steps": steps}
st = os.path.join(d, "status")
if os.path.exists(st):
    out["status"] = open(st).read().split()
mets = sorted(glob.glob(f"{orfs}/logs/asap7/*/base/*.json"))
keep = re.compile(r"(design__instance__count(__stdcell)?$|timing__setup__ws$|timing__hold__ws$|timing__setup__tns$|"
                  r"timing__hold__tns$|route__drc_errors$|global_route__overflow|route__wirelength$|"
                  r"design__instance__utilization$|clock__skew__worst|design__violations$|route__net$|"
                  r"design__instance__count__setup_buffer|design__instance__count__hold_buffer|"
                  r"detailedroute__route__drc_errors|antenna__violating__nets)")
m = {}
for f in mets:
    try:
        j = json.load(open(f))
    except Exception:
        continue
    for k, v in j.items():
        if keep.search(k.split("__", 1)[-1] if False else k) or keep.search(k):
            m[f"{os.path.basename(f)[:-5]}:{k}"] = v
out["metrics"] = m
cs = os.path.join(d, "corner_sta.json")
if os.path.exists(cs):
    try:
        j = json.load(open(cs))
        out["corner_sta"] = {k: j[k] for k in j if not isinstance(j[k], (list,)) and k != "paths"}
    except Exception as e:
        out["corner_sta_err"] = str(e)
ds = os.path.join(d, "docker_stats.log")
if os.path.exists(ds):
    peak_mem, cpus = 0.0, []
    for line in open(ds):
        p = line.split()
        if len(p) < 4:
            continue
        try:
            cpus.append(float(p[2].rstrip("%")) / 100)
            v, u = re.match(r"([\d.]+)([KMGT]i?B)", p[3]).groups()
            g = float(v) * {"KiB": 2**-20, "MiB": 2**-10, "GiB": 1, "TiB": 1024}.get(u, 1)
            peak_mem = max(peak_mem, g)
        except Exception:
            pass
    out["container_samples"] = {"n": len(cpus), "peak_mem_gb": round(peak_mem, 1),
                                "max_threads": round(max(cpus), 1) if cpus else None}
tv = os.path.join(d, "time_v.txt")
if os.path.exists(tv):
    t = open(tv).read()
    g = re.search(r"Elapsed \(wall clock\) time.*: (.*)", t)
    out["total_wall"] = g.group(1) if g else None
print(json.dumps(out, indent=1))
