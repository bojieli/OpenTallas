#!/usr/bin/env python3
"""MESO-INTEG-1 / MESO-RECONCILE-1: bind a count-aligned crossing PLAN (count_align_plan.py --out) to the RTL
parameters it emitted, the start tree and the static schedule, and check it with an independent start-up simulation.

    count_align_bind.py PLAN.json [--table REGIONS.json --table-out REGIONS_CA.json] [--samples 2000] --out BIND.json
    count_align_bind.py OCV.json --from-ocv [--corner ...] [--pad 0] ...        (plans in-process, same plan code)

ONE convention (MESO-RECONCILE-1; COORD 21:55 ruling (4)).  The binder never re-derives K, DEPTH, the start tree or the
origins: it takes the plan's emitted fields (crossings[].rtl{K, DEPTH}, lat_cycles; regions[].origin_cycles,
start_from{parent, port, edge, rtl{PAD, EDGE_FALL}}) and checks them.
  * Frames.  Region v counts from its ORIGIN a_v (first edge whose readers see their start high).  A crossing u -> v with
    RTL K (ot_dp_clk_landing_ca #(.K)) has lag  L = (K + a_v - a_u) T + d  and delivers sender count c at receiver count
    c + K + 1 (RDREG).  Schedule latency sched_lat = K + 1 + a_v - a_u (nominal origins) = plan lat_cycles.
  * Start step on a DIRECTED tree edge p -> x (ot_dp_landing_origin syncing the parent's REGISTERED start, forwarded
    beside the tree port's bus):  a_x - a_p = PAD + 2 + J(d),  J(d) = -floor((d - off) / T),  off = 0 rise / T/2 fall.
    The two lane forms are the SAME quantity counted from different reference edges:
      MESO-COUNT-2: 3 sync flops + PAD + J counted from the parent's start LAUNCH edge a_p - 1;
      MESO-INTEG-1: m + 1 + PAD counted from the parent ORIGIN a_p, m = smallest integer with d + m T >= s,
                    s = T (rise) / 1.5 T (fall), i.e. m = ceil((T + off - d)/T) = 1 - floor((d - off)/T) = 1 + J(d)
                    (ceil(-x) = -floor(x) for every real x), so m + 1 + PAD == PAD + 2 + J(d) identically.
    bind() re-derives every tree step from the MESO-INTEG-1 sync physics and fails on any difference (equality check).
  * RTL K of a tree crossing.  MESO-INTEG-1 fixed K_tree = -1 - PAD + q (lag in [s, s + T) + qT); MESO-COUNT-2 takes
    K = K_eff - n0 with K_eff the smallest count that keeps the derated lag >= 0.5 T + ap (as every other crossing).
    Same origins, same lag formula: the plan's K is equal to MESO-INTEG-1's or one count lower (one cycle less latency
    on that tree crossing); both are inside the ring window.  The loop bench (results/meso_integ_1027/bench) and the
    simulation below run the plan's K.
  * LOOPS: around any closed loop sum(sched_lat) = sum(K + 1) (origin terms telescope): checked per fundamental cycle.
  * verify(): S chips; per tree edge the phase is drawn in its derated interval (+ wander), the child origin is rebuilt
    from the MESO-INTEG-1 sync physics with a metastable sample (+-sync aperture around the boundary) resolved both
    ways at random; every crossing's lag (its own derated d + wander) must lie inside the ring guards
    [0.5 T, (DEPTH - 0.5) T]; reports margins to the guards (COORD 20:35/20:48: gate >= 100 ps; the plan keeps ap = T/8).
"""
import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_plan as CAP  # noqa: E402

SYNC = 3    # ot_dp_landing_origin synchroniser flops (s0, s1, s2); the fall form adds a negedge stage (in s below)
LAUNCH = 1  # the forwarded start is the parent origin's REGISTER output: it rises one parent edge before word 0


class BindError(ValueError):
    pass


def sync_start(edge, T):
    return T if edge == "rise" else 1.5 * T


def integ_step(d, edge, T, pad):
    """MESO-INTEG-1 form: origin step from the parent origin, m = first sampling edge at/after the start arrival"""
    m = math.ceil((sync_start(edge, T) - d) / T)
    return m + SYNC - 1 - LAUNCH + pad


def count2_step(d, edge, T, pad):
    """MESO-COUNT-2 form: PAD + 2 + J(d) (3 sync flops + PAD from the parent's launch edge)"""
    return pad + 2 + CAP.J(d, T, 0.0 if edge == "rise" else T / 2)


def plan_doc(summ, out, regs):
    return dict(summary=summ, regions=regs, crossings=out)


def bind(plan, T=None):
    """plan = count_align_plan.py --out document {summary, regions, crossings}"""
    summ, regs, xs = plan["summary"], plan["regions"], plan["crossings"]
    T = float(summ.get("period_ps", 833.0) if T is None else T)
    if summ.get("regions_reached") != summ.get("regions"):
        raise BindError(f"start tree not spanning: {summ.get('regions_reached')} of {summ.get('regions')} regions")
    bad = [o["port"] for o in xs if not o.get("rtl")]
    if bad:
        raise BindError(f"{len(bad)} crossings have no RTL K/DEPTH (plan FAIL/unreached): {bad[:5]}")
    rows = {o["port"]: o for o in xs}
    n = {g["region"]: int(g["origin_cycles"]) for g in regs}
    root = [g["region"] for g in regs if g["start_from"] is None]
    if len(root) != 1:
        raise BindError(f"need one root region, got {root}")
    regions, tree_ports = {}, {}
    for g in regs:
        e, x = g["start_from"], g["region"]
        if e is None:
            regions[x] = dict(parent=None, tree_port=None, edge_fall=False, pad=int(summ.get("pad", 0)), n_nominal=0,
                              depth=0)
            continue
        p, port, pad = e["parent"], e["port"], int(e["rtl"]["PAD"])
        o = rows[port]
        if (o["src"], o["dst"]) != (p, x):
            raise BindError(f"tree port {port} is not parent {p} -> child {x} (start rides src -> dst only)")
        step = n[x] - n[p]
        if step != e["offset_from_parent"]:
            raise BindError(f"tree edge {port}: origin step {step} != plan offset_from_parent {e['offset_from_parent']}")
        # convention equality on the nominal phase and on both ends of the plan's J deviation interval
        a = integ_step(o["d_ps"], e["edge"], T, pad)
        b = count2_step(o["d_ps"], e["edge"], T, pad)
        if not (a == b == step):
            raise BindError(f"tree edge {port}: MESO-INTEG-1 step {a} / MESO-COUNT-2 step {b} / plan {step} differ")
        regions[x] = dict(parent=p, tree_port=port, edge_fall=bool(e["rtl"]["EDGE_FALL"]), pad=pad, n_nominal=n[x],
                          depth=int(g["tree_depth"]), sync_values=int(e["sync_values"]),
                          sync_dist_ps=e["sync_dist_ps"], start_skew_limit_ps=e.get("start_skew_limit_ps"))
        tree_ports[port] = x
    ports = {}
    for o in xs:
        u, v = o["src"], o["dst"]
        ports[o["port"]] = dict(src=u, dst=v, K=int(o["rtl"]["K"]), depth=int(o["rtl"]["DEPTH"]),
                                sched_lat=int(o["lat_cycles"]), tree=o["port"] in tree_ports, kind=o["kind"],
                                # TRUE derated lag bounds incl. wander (no aperture), and the plan's derated phase
                                # d = dst clock - src clock, so die_sta_related --count-align re-derives L from its own
                                # arrivals: L_sta = L_plan + (d_sta - d_plan)
                                L_lo_ps=o["L_lo_ps"], L_hi_ps=o["L_hi_ps"],
                                d_lo_ps=round(o["d_ps"] - o["p_dn_ps"], 1), d_hi_ps=round(o["d_ps"] + o["p_up_ps"], 1),
                                wander_ps=o.get("wander_ps", 0.0), margin_lo_ps=o["margin_lo_ps"],
                                margin_hi_ps=o["margin_hi_ps"])
    return dict(schema="opentallas.count_align_bind.v2", form="count_aligned", period_ps=T,
                pad=int(summ.get("pad", 0)), root=root[0], ports=ports, regions=regions,
                sync_aperture_ps=summ.get("sync_aperture_ps", 26.5), aperture_ps=summ.get("aperture_ps", T / 8),
                start_skew_limit_min_ps=summ.get("start_skew_limit_min_ps"),
                convention="a_child - a_parent = PAD + 2 + J(d) = MESO-INTEG-1 m + 1 + PAD (identity, checked per edge); "
                           "RTL K = plan K_eff - n0",
                latency_frame="receiver counts; sched_lat = K + 1 + n_dst - n_src (nominal) = plan lat_cycles")


def fundamental_cycles(b):
    """one loop per non-tree crossing: the crossing plus the tree path back; returns [(port, +1/-1 orientation)]"""
    reg = b["regions"]

    def up(x):
        path = []
        while reg[x]["parent"] is not None:
            path.append(x)
            x = reg[x]["parent"]
        return path + [x]
    cyc = []
    for pid, c in b["ports"].items():
        if c["tree"]:
            continue
        pu, pv = up(c["src"]), up(c["dst"])
        common = next(x for x in pu if x in set(pv))
        loop = [(pid, +1)]
        for x in pv[:pv.index(common)]:
            loop.append((reg[x]["tree_port"], -1))
        for x in reversed(pu[:pu.index(common)]):
            loop.append((reg[x]["tree_port"], +1))
        cyc.append(loop)
    return cyc


def verify(b, samples=2000, seed=1, need_ps=100.0):
    T = b["period_ps"]
    sap = float(b.get("sync_aperture_ps", 26.5))
    reg, ports = b["regions"], b["ports"]
    errs = []
    for pid, c in ports.items():
        lhs = c["K"] + 1 + reg[c["dst"]]["n_nominal"] - reg[c["src"]]["n_nominal"]
        if lhs != c["sched_lat"]:
            errs.append(f"identity {pid}: K+1+dn {lhs} != sched_lat {c['sched_lat']}")
    loops = fundamental_cycles(b)
    for lp in loops:
        s1 = sum(sg * ports[p]["sched_lat"] for p, sg in lp)
        s2 = sum(sg * (ports[p]["K"] + 1) for p, sg in lp)
        if s1 != s2:
            errs.append(f"loop {lp[0][0]}: sum sched_lat {s1} != sum(K+1) {s2}")
    rnd = random.Random(seed)
    order = sorted(reg, key=lambda x: reg[x]["depth"])
    worst_lo, worst_hi, bad, worst = math.inf, math.inf, 0, {}
    for i in range(samples):
        mode = i % 3       # 0 uniform, 1 / 2 interval endpoints (mixed)
        dd = {}
        for pid, c in ports.items():
            lo, hi = c["d_lo_ps"], c["d_hi_ps"]
            x = rnd.uniform(lo, hi) if mode == 0 else rnd.choice((lo, hi))
            dd[pid] = x + c["wander_ps"] * rnd.uniform(-1, 1)
        nn = {}
        for x in order:
            r = reg[x]
            if r["parent"] is None:
                nn[x] = 0
                continue
            c = ports[r["tree_port"]]
            # the start was synchronised at a phase inside the derated interval (no post-start wander yet)
            d0 = min(max(dd[r["tree_port"]], c["d_lo_ps"]), c["d_hi_ps"])
            edge = "fall" if r["edge_fall"] else "rise"
            s = sync_start(edge, T)
            ph = (d0 - s) % T                      # distance past the last sampling boundary
            m = math.ceil((s - d0) / T)
            if ph < sap and rnd.random() < 0.5:
                m += 1                             # metastable just after the boundary: resolved late
            elif ph > T - sap and rnd.random() < 0.5:
                m -= 1                             # metastable just before: resolved early
            nn[x] = nn[r["parent"]] + m + SYNC - 1 - LAUNCH + r["pad"]
        for pid, c in ports.items():
            L = (c["K"] + nn[c["dst"]] - nn[c["src"]]) * T + dd[pid]
            ml, mh = L - 0.5 * T, (c["depth"] - 0.5) * T - L
            if ml < worst_lo:
                worst_lo, worst["lo"] = ml, pid
            if mh < worst_hi:
                worst_hi, worst["hi"] = mh, pid
            if ml < 0 or mh < 0:
                bad += 1
    return dict(identity_and_loop_errors=errs, fundamental_cycles=len(loops), samples=samples,
                sim_window_violations=bad, sim_min_margin_low_ps=round(worst_lo, 1),
                sim_min_margin_high_ps=round(worst_hi, 1), sim_worst_ports=worst,
                sim_below_need=bool(min(worst_lo, worst_hi) < need_ps),
                note="margins to the ring guards 0.5T / (DEPTH-0.5)T (COORD 20:35/20:48 gate >= 100 ps); MESO-INTEG-1 "
                     "sync physics with metastable resolution both ways")


def annotate_table(table, b, root_settle_cycles=64):
    """clock_landings / fallback_land region table -> count-aligned form (opt-in; the old ring stays the default)"""
    t = json.loads(json.dumps(table))
    miss = [r["port"] for r in t["ports"] if r["port"] not in b["ports"]]
    if miss:
        raise BindError(f"{len(miss)} table crossings missing from the bind: {miss[:5]}")
    for r in t["ports"]:
        c = b["ports"][r["port"]]
        if (c["src"], c["dst"]) != (r["src_region"], r["dst_region"]):
            raise BindError(f"{r['port']}: bind regions {c['src']}->{c['dst']} != table {r['src_region']}->{r['dst_region']}")
        r["added_cycles"] = c["sched_lat"]
    tp = {r["port"] for r in t["ports"]}
    t["count_aligned"] = dict(schema=b["schema"], period_ps=b["period_ps"], root=b["root"], pad=b["pad"],
                              root_settle_cycles=root_settle_cycles,
                              ports={pid: {k: c[k] for k in ("K", "depth", "sched_lat", "tree")}
                                     for pid, c in b["ports"].items() if pid in tp},
                              regions={k: {x: v[x] for x in ("parent", "tree_port", "edge_fall", "pad")}
                                       for k, v in b["regions"].items()})
    return t


def lane_cycles(table):
    """{lane: added landing cycles} with per-crossing count-aligned latency (or the old +3)"""
    out = defaultdict(int)
    for r in table["ports"]:
        out[r.get("lane")] += int(r.get("added_cycles", 3))
    return dict(out)


def report(b, v):
    hist = defaultdict(int)
    for c in b["ports"].values():
        hist[c["sched_lat"]] += 1
    tree = [c for c in b["ports"].values() if c["tree"]]
    return dict(verify=v, sched_lat_hist=dict(sorted(hist.items())),
                sched_lat_total=sum(c["sched_lat"] for c in b["ports"].values()),
                tree_sched_lat_total=sum(c["sched_lat"] for c in tree),
                old_ring_total=3 * len(b["ports"]),
                depth_hist={str(k): sum(1 for c in b["ports"].values() if c["depth"] == k) for k in (4, 8)},
                K_range=[min(c["K"] for c in b["ports"].values()), max(c["K"] for c in b["ports"].values())],
                start_tree_depth=max(r["depth"] for r in b["regions"].values()),
                tree_edges_fall=sum(1 for r in b["regions"].values() if r["edge_fall"]),
                max_origin_cycles=max(r["n_nominal"] for r in b["regions"].values()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_json", help="count_align_plan.py --out document (or an OCV json with --from-ocv)")
    ap.add_argument("--from-ocv", action="store_true", help="plan in-process from landed_phase_ocv rows")
    ap.add_argument("--corner", default="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5")
    ap.add_argument("--period", type=float, default=833.0)
    ap.add_argument("--aperture", type=float, default=833.0 / 8)
    ap.add_argument("--sync-aperture", type=float, default=26.5)
    ap.add_argument("--wander-frac", type=float, default=0.05)
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--edge-pad", action="append", metavar="PORT=N", help="count_align_plan.py --edge-pad (with --from-ocv)")
    ap.add_argument("--scale", type=float, default=1.0, help="count_align_plan.py --scale (with --from-ocv)")
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--table")
    ap.add_argument("--table-out")
    ap.add_argument("--root-settle", type=int, default=64)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.from_ocv:
        rows = CAP.load_rows(a.plan_json, a.corner, a.scale)
        s, out, regs = CAP.plan(rows, a.period, a.aperture, a.wander_frac, a.sync_aperture, a.pad,
                                CAP.parse_edge_pad(a.edge_pad))
        s.update(period_ps=a.period, aperture_ps=a.aperture, sync_aperture_ps=a.sync_aperture, pad=a.pad, scale=a.scale,
                 wander_frac=a.wander_frac, source=a.plan_json)
        plan = plan_doc(s, out, regs)
    else:
        plan = json.load(open(a.plan_json))
    b = bind(plan)
    v = verify(b, a.samples)
    rep = report(b, v)
    rep["plan_source"] = a.plan_json
    b["report"] = rep
    Path(a.out).write_text(json.dumps(b, indent=0) + "\n")
    if a.table:
        t = annotate_table(json.load(open(a.table)), b, a.root_settle)
        Path(a.table_out).write_text(json.dumps(t, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    ok = not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
