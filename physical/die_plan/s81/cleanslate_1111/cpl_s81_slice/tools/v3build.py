#!/usr/bin/env python3
"""CPL-S81-SLICE SLICE-C S2 street delta (v3, on top of v2): per type, rigid hard-core moves from the hand street
sizing (groupshift), applied to PLAN_IN (99f + v2 + LP-W window + clk_t16 tap), station regs re-sited (resite) or kept
(keep_regs).  Checks the composer gate against the 99f type, the kit tap rule and route_supply; writes PLAN_OUT, the
delta (positions vs PLAN_IN) and a companion (core taps of moved cores + internal stations).
usage: v3build.py PLAN99F PLAN_IN PLAN_OUT OUTDIR SPEC.json   (SPEC: {type: {"moves": {inst: [dx, dy]}, "mode": m}})"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl  # noqa: E402
import common  # noqa: E402
import cgate  # noqa: E402

p99f, pin, pout, od, specf = sys.argv[1:6]
os.makedirs(od, exist_ok=True)
SPEC = json.load(open(specf))
P0, conns = cpl.load(p99f)
P, _ = cpl.load(pin)
raw = json.load(open(pin))
cfg = cpl.rs_cfg()
delta, comp, rows, taps_out = {}, {}, {}, {}
for tn, sp in sorted(SPEC.items()):
    M0 = common.model(P0, conns, tn)
    G = cgate.Gate(p99f, tn, M0.t)
    M = common.model(P, conns, tn)
    pl = list(M.current())
    for inst, (dx, dy) in sp.get("moves", {}).items():
        i = M.ix[inst]
        x, y, o = pl[i]
        pl[i] = (round(x + dx, 3), round(y + dy, 3), o)
    for inst, (ax, ay, ao) in sp.get("abs", {}).items():
        pl[M.ix[inst]] = (ax, ay, ao)
    sp["moves"] = {**sp.get("moves", {}), **sp.get("abs", {})}
    t = M.plan_with(pl)
    for a in (t.get("clock") or {}).get("added_taps", []) or []:
        if a["name"] in sp.get("taps", {}):
            a["xy"] = sp["taps"][a["name"]]
    if sp["mode"] in ("keep_regs", "rigid"):
        t["internal_stations"] = copy.deepcopy(M.t["internal_stations"])
    if sp["mode"] == "rigid":
        # station ends on a moved core translate with that core; regs stay where the plan put them
        p0 = M.current()
        disp = {inst: (pl[M.ix[inst]][0] - p0[M.ix[inst]][0], pl[M.ix[inst]][1] - p0[M.ix[inst]][1]) for inst in sp["moves"]}
        for st in t["internal_stations"]:
            for end, key in (("launch", "from_um"), ("capture", "to_um")):
                who = str(st.get(end, ""))
                hit = [i for i in disp if who == i or who.startswith(i + ".")]
                if hit and st.get(key):
                    dx, dy = disp[max(hit, key=len)]
                    st[key] = [round(st[key][0] + dx, 3), round(st[key][1] + dy, 3)]
    new = G.new(t)
    tp = G.taps(t)
    sc = [q for q in M.station_check(pl) if q not in M.station_check(M.current())]
    r = cpl.RS.analyze_type(M.name, t, cpl.DIE_DIR, cpl.REPO, conns, cfg)
    r.pop("_maps", None)
    r0 = cpl.RS.analyze_type(M0.name, M0.plan_with(M0.current(), resite=False), cpl.DIE_DIR, cpl.REPO, conns, cfg)
    r0.pop("_maps", None)
    rows[tn] = dict(new=new, taps=tp, station_new=sc, p99_99f=r0["worst"]["p99"], p99=r["worst"]["p99"],
                    region=r["worst"]["region"], dir=r["worst"]["dir"],
                    regions={k: v["p99"] for k, v in r["regions"].items() if v["p99"] > 0.8},
                    bitmm_99f=round(M0.bitmm(M0.current()), 1), bitmm=round(M.bitmm(pl), 1),
                    cut=round(max(M.worst_cut(pl)[0][3], M.worst_cut(pl)[1][3]), 3))
    print(tn, json.dumps(rows[tn]), flush=True)
    if new or tp is not None or sc:
        print(tn, "REJECTED", flush=True)
        continue
    raw["partition_types"][tn] = t
    if sp.get("taps"):
        taps_out[tn] = sp["taps"]
    delta[tn] = {inst: [pl[M.ix[inst]][0], pl[M.ix[inst]][1], pl[M.ix[inst]][2]] for inst in sp["moves"]}
    hcs = sorted({h["inst"] for h in t["hard_cores"]}, key=len, reverse=True)

    def own(n):
        return next((i for i in hcs if n == i or n.startswith(i + ".")), None)
    comp[tn] = {"core_taps": {tp_["name"]: tp_["xy"] for tp_ in (t.get("clock") or {}).get("taps", [])
                              if tp_.get("kind") == "core" and own(tp_["name"]) in sp["moves"]},
                "internal_stations": [{k: s[k] for k in ("from_um", "to_um", "regs_um") if k in s}
                                      for s in t.get("internal_stations") or []]}
json.dump(raw, open(pout, "w"), indent=1)
txt = json.dumps(delta, indent=1, sort_keys=True) + "\n"
open(os.path.join(od, "delta_SLICE-C-S2_99f40d35.json"), "w").write(txt)
json.dump(comp, open(os.path.join(od, "companion_SLICE-C-S2.json"), "w"), indent=1, sort_keys=True)
json.dump(rows, open(os.path.join(od, "rows_SLICE-C-S2.json"), "w"), indent=1)
json.dump(taps_out, open(os.path.join(od, "added_taps_SLICE-C-S2.json"), "w"), indent=1, sort_keys=True)
print("adopted", sorted(delta))
