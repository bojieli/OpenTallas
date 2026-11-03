#!/usr/bin/env python3
"""DH58-PROTO: per-port count-aligned K re-plan on the measured l48rf proto clock (the l47k 'record-clock re-plan' form):
for every NON-TREE crossing whose gate CA row (die_sta_related.json count_aligned TT/FF) has a margin < NEED, shift K by the
integer n that maximises min(margin_lo, margin_hi) over TT and FF (margin_lo = L_lo - T/2, margin_hi = (DEPTH - 1/2) T - L_hi,
L moves by n T).  Tree crossings are never touched (they set the start origins).  sched_lat += n (schedule cycles).
usage: k_replan.py BIND GATE_JSON OUT_BIND OUT_DELTA [NEED_PS]"""
import json, sys
bind, gate, ob, od = sys.argv[1:5]; need = float(sys.argv[5]) if len(sys.argv) > 5 else 100.0
b = json.load(open(bind)); g = json.load(open(gate)); T = float(b["period_ps"])
rows = {c: {r["port"]: r for r in g["count_aligned"][c]["rows"]} for c in ("TT", "FF")}
delta = {}
for pid, rt in rows["TT"].items():
    rf = rows["FF"][pid]
    if min(rt["margin_lo_ps"], rt["margin_hi_ps"], rf["margin_lo_ps"], rf["margin_hi_ps"]) >= need:
        continue
    p = b["ports"][pid]
    if p.get("tree"):
        delta[pid] = dict(skipped="tree crossing (start origin)"); continue
    D = p["depth"]
    def score(n):
        return min(min(r["L_lo_ps"] + n * T - T / 2, (D - 0.5) * T - (r["L_hi_ps"] + n * T)) for r in (rt, rf))
    n = max(range(-4, 5), key=score)
    delta[pid] = dict(src=p["src"], dst=p["dst"], K_old=p["K"], K_new=p["K"] + n, dK=n, sched_lat_old=p["sched_lat"],
                      sched_lat_new=p["sched_lat"] + n, margin_after_ps=round(score(n), 1), margin_before_ps=round(score(0), 1))
    p["K"] += n; p["sched_lat"] += n
    # the bind's plan lag L = (K + a_dst - a_src) T + d moves by n T (die_sta_related adds the measured d delta to it)
    p["L_lo_ps"] = round(p["L_lo_ps"] + n * T, 1); p["L_hi_ps"] = round(p["L_hi_ps"] + n * T, 1)
    p["margin_lo_ps"] = round(p["L_lo_ps"] - T / 2, 1); p["margin_hi_ps"] = round((D - 0.5) * T - p["L_hi_ps"], 1)
    p["dh58_proto"] = f"K{n:+d} (l48rf proto-clock re-plan, lep0N region tree)"
json.dump(b, open(ob, "w"))
json.dump(dict(schema="dh58_proto.k_replan.v1", bind=bind, gate=gate, need_ps=need, ports=delta), open(od, "w"), indent=1)
for k, v in delta.items():
    print(k, v)
