#!/usr/bin/env python3
"""QXPQ-FIX/FSTA: aggregate the per-endpoint slack dumps of run_fsta.sh into the receipt.
usage: fsta_report.py STAGE_DIR OUT_JSON   (STAGE_DIR has net/<case>/meta.json and out/<run>.{slk,log})"""
import json, os, re, sys, glob, collections

stage, outp = sys.argv[1:3]
TYPES = {"ot_v41_rom_elem_q_qxpq_w10": "q", "dsfd_qbank_N": "qbank_N", "dsfd_qbank_S": "qbank_S", "ot_s81_cfg7_seq": "cfg7_seq"}
base = lambda p: re.sub(r"\[\d+\]$", "", p.split("/", 1)[1])
runs = {}
for slk in sorted(glob.glob(os.path.join(stage, "out", "*.slk"))):
    r = os.path.basename(slk)[:-4]
    case, corner, w, tag = r.split("_")
    meta = json.load(open(os.path.join(stage, "net", case, "meta.json")))
    inst = meta["instances"]
    drv = {}
    for n in meta["timed_nets"]:
        for s, L in zip(n["sinks"], n["len_um"]):
            drv[s] = (n["drv"], L)
    sl = {}
    for ln in open(slk):
        p, smax, smin = ln.split()
        sl[p] = (float(smax) if smax != "INF" else None, float(smin) if smin != "INF" else None)
    groups = collections.defaultdict(lambda: {"n": 0, "setup": None, "hold": None, "setup_pin": None, "hold_pin": None, "max_len_um": 0})
    unconstrained = collections.Counter()
    for s, (d, L) in drv.items():
        st, dt = TYPES[inst[d.split("/")[0]]["type"]], TYPES[inst[s.split("/")[0]]["type"]]
        key = "%s.%s -> %s.%s" % (st, base(d), dt, base(s))
        g = groups[key]
        g["n"] += 1
        g["max_len_um"] = max(g["max_len_um"], L)
        if s not in sl:
            unconstrained[key] += 1
            continue
        smax, smin = sl[s]
        if smax is not None and (g["setup"] is None or smax < g["setup"]):
            g["setup"], g["setup_pin"] = round(smax, 2), "%s -> %s" % (d, s)
        if smin is not None and (g["hold"] is None or smin < g["hold"]):
            g["hold"], g["hold_pin"] = round(smin, 2), "%s -> %s" % (d, s)
    pairs = collections.defaultdict(lambda: {"setup": None, "hold": None})
    for k, g in groups.items():
        a, b = k.split(" -> ")
        pk = "%s -> %s" % (a.split(".")[0], b.split(".")[0])
        for m in ("setup", "hold"):
            if g[m] is not None and (pairs[pk][m] is None or g[m] < pairs[pk][m]):
                pairs[pk][m] = g[m]
    log = open(os.path.join(stage, "out", r + ".log")).read()
    trunk = float(re.search(r"FSTA corner \S+ spef \S+ trunk (\S+)", log).group(1))
    runs[r] = {"case": case, "corner": corner, "wire": w == "w1", "trunk_ps": trunk, "tag": tag,
               "endpoints": len(sl), "unconstrained_sinks": dict(unconstrained),
               "worst_setup": min(v["setup"] for v in pairs.values() if v["setup"] is not None),
               "worst_hold": min(v["hold"] for v in pairs.values() if v["hold"] is not None),
               "pairs": dict(pairs), "pin_groups": dict(groups)}
json.dump(runs, open(outp, "w"), indent=1, sort_keys=True)
for r, v in runs.items():
    print(r, "setup %.1f hold %.1f" % (v["worst_setup"], v["worst_hold"]),
          " | ".join("%s S%.1f H%.1f" % (k, p["setup"], p["hold"]) for k, p in sorted(v["pairs"].items())),
          "uncon", sum(v["unconstrained_sinks"].values()))
