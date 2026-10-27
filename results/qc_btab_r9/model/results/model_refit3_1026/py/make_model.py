#!/usr/bin/env python3
"""MODEL-REFIT-3: write the versioned phys_gate fit file from fit3_grt.json (GRT basis).  usage: make_model.py fit3_grt.json OUT.json"""
import hashlib, json, math, sys
F = json.load(open(sys.argv[1]))
def loomax(kind, C, fam=None):
    return max(v["test"][C]["maxabs"] for b, v in F["loo"][kind].items() if fam is None or fam(b))
qc = lambda b: not b.startswith("head")
pmax = dict(F["fits"]["max"]["params"], kleaf=F["kleaf"]); pmin = dict(F["fits"]["min"]["params"], kleaf=F["kleaf"])
lt, lf = loomax("max", "TT"), loomax("min", "FF")
out = dict(name="uf_phys3 v1 (MODEL-REFIT-3 2026-10-26): uf_phys + KSTAGE + BLEAF, GRT basis, %d builds" % len(F["builds"]),
           model="uf_phys3", basis="GRT (5_1_grt meas_ck, rc_cal 0.8/0.9); NOT an RCX predictor (see fit_rcx.json / island_shift.json)",
           PMAX=pmax, PMIN=pmin,
           LOO_maxabs={"TT_max_analysis": {b: v["test"]["TT"]["maxabs"] for b, v in F["loo"]["max"].items()},
                       "FF_min_analysis": {b: v["test"]["FF"]["maxabs"] for b, v in F["loo"]["min"].items()}},
           LOO_window_err={"TT": {b: v["test"]["TT"]["window_err"] for b, v in F["loo"]["max"].items()},
                           "FF": {b: v["test"]["FF"]["window_err"] for b, v in F["loo"]["min"].items()}},
           LOO_MAX={"TT": math.ceil(lt), "FF": math.ceil(lf)},
           LOO_MAX_QC_ONLY={"TT": math.ceil(loomax("max", "TT", qc)), "FF": math.ceil(loomax("min", "FF", qc))},
           builds=F["builds"], source=sys.argv[1], source_sha256=hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(),
           note="guard = LOO max per-leaf |err| over all builds, rounded up; calibration only, no per-build offset (12.8). UNCHECKED.")
wu = {C: max(0.0, -min(v["test"][C]["window_err"] for v in F["loo"][k].values())) for k, C in (("max", "TT"), ("min", "FF"))}
out["WIN_GUARD"] = {C: math.ceil(x) for C, x in wu.items()}
out["WIN_GUARD_note"] = ("LOO window UNDER-prediction max (TT %.2f, FF %.2f), rounded up; phys_gate window limit = 20 - max(WIN_GUARD). "
                         "Over-prediction (HEAD +4..+11) is the safe side." % (wu["TT"], wu["FF"]))
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(json.dumps({k: out[k] for k in ("PMAX", "PMIN", "LOO_MAX", "LOO_MAX_QC_ONLY", "LOO_window_err")}, indent=0))
