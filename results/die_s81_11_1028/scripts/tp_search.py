#!/usr/bin/env python3
"""DIE-S81-11 step (1): greedy per-pair --tree-parent override search on the CA-OCV-1 plan form (same args as
die-s81-10 gate_s10.sh).  Rows are built exactly as count_align_plan.main (load_rows + sta_hull with
sta_d_intervals, clock_ocv table, shared droop) and cached; plan() is then called with skew_clean as the gate."""
import json, os, sys, time, copy
MT = sys.argv[1]; OUT = sys.argv[2]
sys.path.insert(0, MT)
import count_align_plan as C
X = "/srv/opentallas-scratch2/claude/die-s81-8/gate_sspice/sp_xing_lpo.json"
PR = "/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body/proof_body"
PL = "/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json"
CORN = "TT_droop-regions_corelat250,FF_droop-regions_corelat202.5"
SK = (46.9, 79.4)
cache = os.path.join(OUT, "rows_hull.json")
if os.path.exists(cache):
    rows = json.load(open(cache))
else:
    import die_sta_related as DSR
    rows = C.load_rows(X, CORN, 1.0)
    info = C.sta_hull(rows, DSR.sta_d_intervals(PR, PL, ["FF", "TT"], "spice", True, clock_ocv="table",
                                                clock_droop="shared", droop_regions_file=PR + "/droop_regions.json",
                                                core_latency_ff=202.5))
    print("hull", info)
    json.dump(rows, open(cache, "w"))

def run(tp):
    s, out, regs = C.plan(copy.deepcopy(rows), 833.0, 833.0 / 8, 0.05, 26.5, 0, None, SK, True, tree_parent=tp or None)
    return s, out, regs

def score(s, out):
    f = [o for o in out if not o.get("depth")]
    exc = sum(max(0.0, o["L_hi_ps"] - (7.5 * 833 - 104.125)) for o in f)
    return (len(f), exc)

import multiprocessing as mp
byport = {r["port"]: r for r in rows}
SYN = {}
for r in rows:
    q = dict(r); q["lo"], q["hi"] = q["d_ps"] - q["p_dn_ps"], q["d_ps"] + q["p_up_ps"]
    nv, edge, off, dist = C.sync_choice(q, 833.0, 833.0 / 8, SK, 26.5)
    SYN[r["port"]] = (nv, dist)

def evalc(j):
    t2, x, port = j
    try:
        s, o2, _ = run(t2)
    except ValueError:
        return None
    return (score(s, o2), x, port, s, o2)

t = time.time()
s0, out0, regs0 = run({})
print("base fail", s0["fail"], "t", round(time.time() - t, 1), flush=True)
tp = {}
cur = score(s0, out0); out = out0
for it in range(30):
    fails = [o for o in out if not o.get("depth")]
    if not fails:
        break
    pairs = sorted({(o["src"], o["dst"]) for o in fails})
    cands = []
    for (u, v) in pairs:
        for (a, b) in ((u, v), (v, u)):
            for r in rows:
                if r["src"] == a and r["dst"] == b:
                    cands.append((b, r["port"]))
    cands = list(dict.fromkeys(cands))
    # keep the 2 ports per (child, src) with the largest sync distance (clean first)
    grp = {}
    for (x, port) in cands:
        r = byport[port]; grp.setdefault((x, r["src"]), []).append(port)
    cands = []
    for (x, src), ps in grp.items():
        ps.sort(key=lambda q: (-(SYN[q][0] == 1), -SYN[q][1]))
        cands += [(x, q) for q in ps[:2]]
    jobs = [(dict(tp, **{x: port}), x, port) for (x, port) in cands]
    best = None
    with mp.get_context("fork").Pool(10) as pool:
        for res in pool.imap_unordered(evalc, jobs):
            if res is None:
                continue
            sc, x, port, s, o2 = res
            if sc < cur and (best is None or sc < best[0]):
                best = (sc, x, port, s, o2)
    if best is None:
        print("no improving override; stop", flush=True)
        break
    cur, x, port, s, out = best
    tp[x] = port
    print(f"it {it}: {x}={port} -> fail {cur[0]} excess {cur[1]:.0f} lo {s['worst_margin_lo_ps']} hi {s['worst_margin_hi_ps']}", flush=True)
s, out, regs = run(tp)
n, bad, wl, wh = C.mc_check(copy.deepcopy(rows) if False else [dict(r, lo=r["d_ps"]-r["p_dn_ps"], hi=r["d_ps"]+r["p_up_ps"]) for r in rows], out, regs, 833.0, 500, 26.5, start_skew=SK)
s["mc"] = dict(chips=n, violations=bad, worst_lo=wl, worst_hi=wh)
s["tree_parent"] = tp
json.dump(dict(summary=s, regions=regs, crossings=out), open(os.path.join(OUT, "plan_tp.json"), "w"), indent=0)
fails = [o for o in out if not o.get("depth")]
print(json.dumps(dict(fail=s["fail"], d4=s["depth4"], d8=s["depth8"], lo=s["worst_margin_lo_ps"], hi=s["worst_margin_hi_ps"],
                      amb_edges=len(s["tree_edges_ambiguous"]), lat=s["lat_total_vs_old3"], mc=s["mc"], tp=tp,
                      skew=s.get("start_skew_clean", {}).get("padded_edges")), indent=1))
for o in fails:
    print("FAIL", o["port"], o["src"], o["dst"], "amb", o["path_ambiguous_cycles"], "Lw", o["L_width_ps"], "Lhi", o["L_hi_ps"])
