"""DIE-HEAD-29: HEAD START gate start-port row (die_sta_related.count_align_start_ports, as HEAD-START-4 gate_pred.py /
probe_corelat.py) on the routed proof_r1 with the V1 measured START data delay, with the tool tree TOOLS as is (old =
origin/main, new = per-tap virtual START rule).  usage: probe_dh29.py TOOLS PLAN DD PROOF CAL CTXPLAN OUT"""
import json, sys, collections
sys.path.insert(0, sys.argv[1])
import count_align_bind as CAB, count_align_plan as CAP, die_sta_related as DSR
plan = json.load(open(sys.argv[2])); dd = json.load(open(sys.argv[3]))["ports"]; proof = sys.argv[4]; cal = sys.argv[5]
b = CAB.bind(plan)
out = dict(tools=sys.argv[1], has_rule=hasattr(DSR, "is_start_virtual_tap"))
for c in ("TT", "FF"):
    ctx = CAP.clock_contexts(proof, sys.argv[6], [c], cal, "table", "shared", proof + "/droop_regions.json", 380.0, "inv2")[c]
    taps = dict(ctx["taps"])
    sp = b.get("start_ports", {})
    old, DSR.CPPR_LCA = DSR.CPPR_LCA, True
    try:
        rec = collections.defaultdict(dict)

        def ocv(x, y, chk, f=ctx["ocv"]):
            v = f(x, y, chk)
            rec[(x, y)][chk] = v
            return v
        rows = DSR.count_align_start_ports(b, taps, ctx["meta"], plan["summary"]["period_ps"], ctx["rng"], ocv, 26.5,
                                           data_delay={p: tuple(v) for p, v in dd.items()})
    finally:
        DSR.CPPR_LCA = old
    meas = [r for r in rows if r["port"] in dd]
    ds = sorted(r["sta_sync_dist_ps"] for r in meas if "sta_sync_dist_ps" in r)
    pess = sorted(v["setup"] + v["hold"] for v in rec.values() if "setup" in v and "hold" in v)
    out[c] = dict(ocv_pairs=len(pess), ocv_setup_plus_hold_ps_median=round(pess[len(pess) // 2], 1) if pess else None,
                  ocv_setup_plus_hold_ps_max=round(pess[-1], 1) if pess else None,
                  pair_kinds=collections.Counter(str((x.startswith("__st__"),
                                                      y.startswith("__st__"))) for x, y in rec),
                  ports=len(rows), measured=len(meas), measured_fail=sum(not r["ok"] for r in meas),
                  unmeasured_fail_closed=sum(1 for r in rows if r["port"] not in dd),
                  unmeasured_ok=sum(1 for r in rows if r["port"] not in dd and r["ok"]),
                  min_sync_dist=ds[0] if ds else None, below_100=sum(1 for x in ds if x < 100),
                  reasons=collections.Counter(r.get("reason", "ok" if r["ok"] else "dist<ap") for r in rows))
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(sys.argv[7], "w"), indent=1, default=str)
