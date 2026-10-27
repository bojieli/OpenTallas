"""PATH-S81-PD13: what-if proof dir for the SHARED die STA (model only, UNCHECKED).  A faster tree above the mesh shifts
every mesh load (and leaf-fed band root) by sh(l) = new sim nominal - old sim nominal; the stubs below are unchanged, so
the routed stub arrivals (mesh_<C>.json) and the tap arrivals (tap_arrivals_<C>.json, late+early, taps + spine dicts) are
shifted by sh of their load.  The routed-vs-sim RC gap per load is therefore the measured one (kept).  Every other file is
a symlink to the routed build.
usage: mkproof.py SRC_BUILD OUT_DIR OLD_TT NEW_TT OLD_FF NEW_FF"""
import json, os, sys
src, out, oTT, nTT, oFF, nFF = sys.argv[1:7]
os.makedirs(out, exist_ok=True)
skip = {"tap_arrivals_TT.json", "tap_arrivals_FF.json", "mesh_TT.json", "mesh_FF.json"}
for f in os.listdir(src):
    if f not in skip and not os.path.exists(os.path.join(out, f)):
        os.symlink(os.path.join(os.path.abspath(src), f), os.path.join(out, f))
M = json.load(open(os.path.join(src, "mesh.json")))
load = {t["port"]: (t.get("mesh_in") or t["stub"]) for t in M["taps"]}
rep = {}
for C, op, np_ in (("TT", oTT, nTT), ("FF", oFF, nFF)):
    O = json.load(open(op)); N = json.load(open(np_))
    o0 = dict(zip(O["loads"], O["arr"][0])); n0 = dict(zip(N["loads"], N["arr"][0]))
    sh = {k: n0[k] - o0[k] for k in o0 if k in n0}
    R = json.load(open(os.path.join(src, f"mesh_{C}.json")))
    miss = 0
    for k, v in R["stubs"].items():
        if k in sh: v["late"] += sh[k]; v["early"] += sh[k]
        else: miss += 1
    json.dump(R, open(os.path.join(out, f"mesh_{C}.json"), "w"))
    A = json.load(open(os.path.join(src, f"tap_arrivals_{C}.json")))
    tmiss = 0
    for t in A["taps"]:
        s = sh.get(load.get(t["port"]))
        if s is None: tmiss += 1; continue
        t["late_ps"] += s; t["early_ps"] += s
        for key, fld in (("spine_late", "late_ps"), ("spine_early", "early_ps")):
            if t["part"] in A.get(key, {}) and t["tap"] in A[key][t["part"]]:
                A[key][t["part"]][t["tap"]] = t[fld]
    json.dump(A, open(os.path.join(out, f"tap_arrivals_{C}.json"), "w"))
    v = sorted(sh.values())
    rep[C] = dict(shift_min=round(v[0], 1), shift_max=round(v[-1], 1), stub_miss=miss, tap_miss=tmiss)
print(json.dumps(rep))
