"""DIE-HEAD-28 diagnostic (no waiver): does clock_ocv_fn.branch charge the global class-B core latency (450 TT / 380 FF)
to virtual START taps (part None)?  Re-runs the gate start-port row (count_align_start_ports, as gate_pred.py) on the
routed proof_r1 with the V1 measured data delay, (a) as-is and (b) with core_lat = 0 for pairs whose two taps are both
outside hard cores (part None).  usage: probe_corelat.py TOOLS PLAN DD PROOF CAL CTXPLAN OUT"""
import json, sys, collections
sys.path.insert(0, sys.argv[1])
import count_align_bind as CAB, count_align_plan as CAP, die_sta_related as DSR
plan = json.load(open(sys.argv[2])); dd = json.load(open(sys.argv[3]))["ports"]; proof = sys.argv[4]; cal = sys.argv[5]
b = CAB.bind(plan)
orig = DSR.clock_ocv_fn
MODE = {"zero": False}
def patched(mode, droop, meta, taps, core_lat, *a, **k):
    f = orig(mode, droop, meta, taps, core_lat, *a, **k)
    f0 = orig(mode, droop, meta, taps, 0.0, *a, **k)
    def fn(x, y, check):
        if MODE["zero"] and taps[x].get("part") is None and taps[y].get("part") is None:
            return f0(x, y, check)
        return f(x, y, check)
    return fn
DSR.clock_ocv_fn = patched
out = {}
for c in ("TT", "FF"):
    ctx = CAP.clock_contexts(proof, sys.argv[6], [c], cal, "table", "shared", proof + "/droop_regions.json", 380.0, "inv2")[c]
    taps = dict(ctx["taps"])
    sp = b.get("start_ports", {})
    kinds = collections.Counter((taps.get(v["launch"], {}).get("part") is None, taps.get(v["capture"], {}).get("part") is None) for v in sp.values())
    res = {}
    for z in (False, True):
        MODE["zero"] = z
        old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
        try:
            rows = DSR.count_align_start_ports(b, taps, ctx["meta"], plan["summary"]["period_ps"], ctx["rng"], ctx["ocv"], 26.5,
                                               data_delay={p: tuple(v) for p, v in dd.items()})
            pess = [ctx["ocv"](v["launch"], v["capture"], "setup") + ctx["ocv"](v["launch"], v["capture"], "hold")
                    for v in sp.values() if v["launch"] in taps and v["capture"] in taps]
        finally:
            DSR.CPPR_LCA = old
        meas = [r for r in rows if r["port"] in dd]
        ds = sorted(r["sta_sync_dist_ps"] for r in meas if "sta_sync_dist_ps" in r)
        res["corelat0_virtual" if z else "as_is"] = dict(
            ports=len(rows), measured=len(meas), measured_fail=sum(not r["ok"] for r in meas),
            unmeasured_fail_closed=sum(1 for r in rows if r["port"] not in dd), min_sync_dist=ds[0] if ds else None,
            below_100=sum(1 for x in ds if x < 100), ocv_setup_plus_hold_ps_max=round(max(pess), 1),
            ocv_setup_plus_hold_ps_median=round(sorted(pess)[len(pess) // 2], 1))
    res["tap_kinds_(launch_virtual,capture_virtual)"] = {str(k): v for k, v in kinds.items()}
    out[c] = res
print(json.dumps(out, indent=1))
json.dump(out, open(sys.argv[7], "w"), indent=1)
