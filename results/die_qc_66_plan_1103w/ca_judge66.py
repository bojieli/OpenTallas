# DIE-QC-66/CLK: count-aligned landed check of the AS-BUILT ring (plan count_aligned_cycles P, sidecar DEPTH) on a
# die clock proof, with THE gate interval model (die_sta_related.sta_port_intervals = what --count-align times).
# Lag of word n (clean START, nominal origins): L = (K + a_dst - a_src) T + d = (sched_lat - 1) T + d  (count_align_bind
# convention sched_lat = K + 1 + a_v - a_u).  Guards (count_align_bind / gate): L_lo - T/2 >= 100 ps,
# (DEPTH - 0.5) T - L_hi >= 100 ps; wander +-0.05 x unshared (gate wfrac, full, plan wander credit not taken).
# usage: ca_judge66.py PROOF PLAN BIND_ASBUILT OUT.json [cycles_delta.json]
import json, sys, collections
sys.path.insert(0, "/srv/opentallas-scratch3/claude/dq66-dieprobe/src/tools/die_plan")
import die_sta_related as S
proof, planf, bindf, out = sys.argv[1:5]
delta = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
T = 833.0; G = 100.0
plan = json.load(open(planf)); b = json.load(open(bindf))
P = plan["clock"]["landing_network"]["count_aligned_cycles"]
iv = S.sta_port_intervals(proof, plan, ("TT", "FF"), b["ports"], cppr_lca=True, clock_cell="inv2", margin_policy="nominal")
rows, summ = [], {}
for c in ("TT", "FF"):
    r = iv[c]["rise"]; ush = iv[c]["unshared"] or {}
    nt, fl = 0, []
    wl, wh = None, None
    for pid, cb in b["ports"].items():
        x = r.get(pid)
        if x is None:
            nt += 1; continue
        p = P[pid] + int(delta.get(pid, 0)); D = int(cb["depth"]); w = 0.05 * ush.get(pid, 0.0)
        lo = (p - 1) * T + x[0] - w; hi = (p - 1) * T + x[1] + w
        mlo, mhi = lo - 0.5 * T, (D - 0.5) * T - hi
        rows.append(dict(corner=c, port=pid, cycles=p, depth=D, d_lo=round(x[0], 1), d_hi=round(x[1], 1), wander=round(w, 1),
                         margin_lo=round(mlo, 1), margin_hi=round(mhi, 1)))
        if wl is None or mlo < wl[0]: wl = (round(mlo, 1), pid)
        if wh is None or mhi < wh[0]: wh = (round(mhi, 1), pid)
        if mlo < G or mhi < G: fl.append((pid, round(mlo, 1), round(mhi, 1)))
    summ[c] = dict(crossings=len(b["ports"]) - nt, no_taps=nt, unbound=len(iv[c]["unbound"]), worst_lo=wl, worst_hi=wh,
                   fail=len(fl), fail_lo=sum(1 for f in fl if f[1] < G), fail_hi=sum(1 for f in fl if f[2] < G), fails=fl)
fp = collections.defaultdict(dict)
for c in summ:
    for pid, mlo, mhi in summ[c]["fails"]:
        fp[pid][c] = (mlo, mhi)
fix = {}
for pid, v in fp.items():
    lo = min(m[0] for m in v.values()); hi = min(m[1] for m in v.values())
    if lo < G and hi - T >= G: fix[pid] = 1
    elif hi < G and lo - T >= G: fix[pid] = -1
    else: fix[pid] = None
summ["fix"] = dict(plus1=sorted(p for p, f in fix.items() if f == 1), minus1=sorted(p for p, f in fix.items() if f == -1),
                   no_single_cycle_fix=sorted(p for p, f in fix.items() if f is None))
json.dump(dict(summary=summ, rows=rows), open(out, "w"))
for c in ("TT", "FF"):
    s = summ[c]; print(c, {k: v for k, v in s.items() if k != "fails"})
print("fix +1", len(summ["fix"]["plus1"]), "-1", len(summ["fix"]["minus1"]), "none", len(summ["fix"]["no_single_cycle_fix"]))
json.dump({p: f for p, f in fix.items() if f}, open(out.replace(".json", "_delta.json"), "w"))
