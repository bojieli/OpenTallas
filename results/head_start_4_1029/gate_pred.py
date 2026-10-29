"""HEAD-START-4: gate prediction for a V1 plan: die_sta_related.count_align_start_ports (the gate start-port row) on the
ROUTED proof (head-start-3 proof_r1, TT and FF) with the measured START data delay; plus coverage of the 513 as-built fails."""
import json, sys, collections
sys.path.insert(0, sys.argv[1])
import count_align_bind as CAB, count_align_plan as CAP, die_sta_related as DSR
plan = json.load(open(sys.argv[2])); dd = json.load(open(sys.argv[3]))["ports"]; proof = sys.argv[4]; cal = sys.argv[5]
b = CAB.bind(plan)
out = {}
for c in ("TT", "FF"):
    ctx = CAP.clock_contexts(proof, sys.argv[6], [c], cal, "table", "shared", proof + "/droop_regions.json",
                             380.0, "inv2")[c]
    taps = dict(ctx["taps"])  # measured __st__ START clock taps of the routed proof are kept (as die_sta_related)
    old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
    try:
        rows = DSR.count_align_start_ports(b, taps, ctx["meta"], plan["summary"]["period_ps"], ctx["rng"], ctx["ocv"], 26.5,
                                           data_delay={p: tuple(v) for p, v in dd.items()})
    finally:
        DSR.CPPR_LCA = old
    meas = [r for r in rows if r["port"] in dd]
    out[c] = dict(ports=len(rows), measured=len(meas), measured_fail=sum(not r["ok"] for r in meas),
                  unmeasured_fail_closed=sum(1 for r in rows if r["port"] not in dd),
                  min_sync_dist_measured=min((r["sta_sync_dist_ps"] for r in meas if "sta_sync_dist_ps" in r), default=None),
                  below_100=sum(1 for r in meas if r.get("sta_sync_dist_ps", 1e9) < 100),
                  reasons=collections.Counter(r.get("reason", "ok" if r["ok"] else "dist<ap") for r in rows))
rows513 = [r for r in json.load(open(sys.argv[7]))["rows"] if r["asbuilt"] < 0]
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(sys.argv[8], "w"), indent=1, default=str)
if len(sys.argv) > 9:
    E = {e["port"]: e for e in plan["start_edges"]}
    worst = sorted((r for r in rows if r["port"] in dd and "sta_sync_dist_ps" in r), key=lambda r: r["sta_sync_dist_ps"])[:5]
    for r in worst:
        e = E[r["port"]]
        print(json.dumps(dict(port=r["port"][:40], edge=r["edge"], gate_d=[r["d_lo_ps"], r["d_hi_ps"]], dist=r["sta_sync_dist_ps"],
                              plan_clock=e.get("clock_interval_ps"), dd=e.get("data_delay_ps"), plan_iv=[round(e["lo"],1), round(e["hi"],1)],
                              fall=[e.get("fall_lo"), e.get("fall_hi")], d=e["d_ps"]), ensure_ascii=True))
