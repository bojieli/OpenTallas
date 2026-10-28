#!/usr/bin/env python3
"""MESO-INTEG-1: bind a count-aligned crossing plan (count_align_plan.py) to RTL parameters, a start tree and the
static schedule, and check it with an independent physical start-up simulation.

    count_align_bind.py OCV_JSON [--corner ...] [--pad 0] [--table REGIONS.json --table-out REGIONS_CA.json]
                        [--samples 2000] --out BIND.json

Frames (results/meso_integ_1027/README.md):
  * Every region v counts from its own ORIGIN n_v (abs cycle of its count 0).  A crossing u -> v with RTL read offset K
    (ot_dp_clk_landing_ca #(.K)) gives lag  L = (K + n_v - n_u) T + d  and delivers sender count c at receiver count
    c + K + 1 (RDREG): K + 1 is the latency in RECEIVER counts, the same on every chip.
  * Origins: root = ot_dp_landing_root (fixed settle count after the raw reset); child = ot_dp_landing_origin on the
    tree port (parent -> child) with K_tree = -2 - PAD, so the tree crossing's lag is the sync window [s, s + T),
    s = T (rise) / 1.5 T (fall); then n_child - n_parent = m + 2 + PAD, m = the smallest integer with d + m T >= s.
  * Schedule latency of a crossing = K + 1 + (n_v - n_u) at the NOMINAL origins = the plan's lat_cycles (K + n0 + 1).
    It is a compile-time constant per crossing.  It is the latency the 10-14 static schedule and TOK pricing use: the
    die START wavefront rides the same landed crossings, so every region runs the schedule in its own counts and a
    word priced at sched_lat arrives exactly there, on every chip (the per-chip origin ambiguity of a path only moves
    L inside the ring window, which the plan sized for it).
  * LOOPS: around any closed loop of crossings sum(sched_lat) = sum(K + 1) (the origin terms telescope), so the
    schedule is consistent around loops by construction and a token loop's cycle count does not depend on the
    start tree.  verify() checks the identity per crossing and on every fundamental cycle, then simulates S chips:
    per-tree-edge phase drawn in its derated interval, origins rebuilt from the sync physics (not from the plan's
    ambiguity arithmetic), per-crossing phase + wander drawn, and the lag of EVERY crossing checked against
    [(0.5 T + ap), (DEPTH - 0.5) T - ap] (COORD 20:35 margin definition) -> min low/high margin.
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

SYNC = 3  # ot_dp_landing_origin synchroniser flops (rise); fall adds the half-cycle negedge stage (in s)
# MESO-INTEG-1 loop bench (results/meso_integ_1027/bench): in the die wiring the forwarded start is the parent origin's
# REGISTER output: it rises right after parent edge e, while the parent's rings write word 0 at edge e + 1 (first edge
# that samples t_rst_n high).  The child sync therefore sees the start one parent period before word 0 (tb_ca_tree drove
# p_start AT the word-0 edge).  The origin step is one count shorter and the tree K one count larger than MESO-COUNT-1's
# -2 - PAD; the physical lag L is unchanged.
LAUNCH = 1


class BindError(ValueError):
    pass


def sync_start(edge, T):
    return T if edge == "rise" else 1.5 * T


def bind(summ, out, T=833.0, pad=0):
    tr = summ["_tree"]
    rows = {o["port"]: o for o in out}
    if summ["tree_components"] != 1:
        raise BindError(f"start tree not spanning: {summ['tree_components']} components")
    if summ.get("tree_edges_reversed"):
        raise BindError(f"tree edges run child -> parent (need a start-only wire, not built): {summ['tree_edges_reversed']}")
    if summ["fail"]:
        raise BindError(f"{summ['fail']} crossings have no DEPTH (plan FAIL)")
    n = {tr["root"]: 0}
    k_tree = -2 + LAUNCH - pad
    for x in tr["order"][1:]:
        p, port = tr["parent"][x]
        o = rows[port]
        if (o["src"], o["dst"]) != (p, x):
            raise BindError(f"tree port {port} is not parent {p} -> child {x}")
        m = o["lat_cycles"] - 1 - o["tree_shift"]
        if tr["a0"][x] - tr["a0"][p] != m:
            raise BindError(f"tree edge {port}: plan origin step {tr['a0'][x] - tr['a0'][p]} != sync step {m}")
        n[x] = n[p] + m + SYNC - 1 - LAUNCH + pad
    tree_ports = {port for _, port in tr["parent"].values()}
    ports = {}
    for o in out:
        u, v = o["src"], o["dst"]
        K = k_tree + o["tree_shift"] if o["port"] in tree_ports else o["lat_cycles"] - 1 - (n[v] - n[u])
        ports[o["port"]] = dict(src=u, dst=v, K=K, depth=o["depth"], sched_lat=o["lat_cycles"],
                                tree=o["port"] in tree_ports, L_lo_ps=o["L_lo_ps"], L_hi_ps=o["L_hi_ps"],
                                # plan derated phase d = dst clock - src clock (no aperture) + tree wander, so the shared
                                # die STA (die_sta_related --count-align) can re-derive L from its own arrivals
                                d_lo_ps=round(o["d_ps"] - o["p_dn_ps"], 1), d_hi_ps=round(o["d_ps"] + o["p_up_ps"], 1),
                                wander_ps=o.get("wander_ps", 0.0))
    regions = {tr["root"]: dict(parent=None, tree_port=None, edge_fall=False, pad=pad, n_nominal=0, depth=0)}
    for x in tr["order"][1:]:
        p, port = tr["parent"][x]
        regions[x] = dict(parent=p, tree_port=port, edge_fall=tr["edge"][x] == "fall", pad=pad, n_nominal=n[x],
                          depth=tr["depth"][x])
    return dict(schema="opentallas.count_align_bind.v1", form="count_aligned", period_ps=T, pad=pad, k_tree=k_tree,
                root=tr["root"], ports=ports, regions=regions,
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
        # v -> common: walk up from v, each tree edge (parent -> x) traversed against its direction
        for x in pv[:pv.index(common)]:
            loop.append((reg[x]["tree_port"], -1))
        # common -> u: down the tree, along the tree port directions
        for x in reversed(pu[:pu.index(common)]):
            loop.append((reg[x]["tree_port"], +1))
        cyc.append(loop)
    return cyc


def verify(b, rows_by_port, samples=2000, ap=None, wander_frac=0.05, seed=1):
    T = b["period_ps"]
    ap = T / 8 if ap is None else ap
    reg, ports = b["regions"], b["ports"]
    errs = []
    # (1) per-crossing frame identity
    for pid, c in ports.items():
        lhs = c["K"] + 1 + reg[c["dst"]]["n_nominal"] - reg[c["src"]]["n_nominal"]
        if lhs != c["sched_lat"]:
            errs.append(f"identity {pid}: K+1+dn {lhs} != sched_lat {c['sched_lat']}")
    # (2) loops: sum(sched_lat) == sum(K + 1) on every fundamental cycle (signed)
    loops = fundamental_cycles(b)
    for lp in loops:
        s1 = sum(sg * ports[p]["sched_lat"] for p, sg in lp)
        s2 = sum(sg * (ports[p]["K"] + 1) for p, sg in lp)
        if s1 != s2:
            errs.append(f"loop {lp[0][0]}: sum sched_lat {s1} != sum(K+1) {s2}")
    # (3) physical start-up simulation
    rnd = random.Random(seed)
    order = sorted(reg, key=lambda x: reg[x]["depth"])
    lo_edge, worst_lo, worst_hi, bad = 0.5 * T + ap, math.inf, math.inf, 0
    worst = {}
    for _ in range(samples):
        nn, dtree = {b["root"]: 0}, {}
        for x in order:
            r = reg[x]
            if r["parent"] is None:
                continue
            row = rows_by_port[r["tree_port"]]
            d = dtree[x] = rnd.uniform(row["d_ps"] - row["p_dn_ps"], row["d_ps"] + row["p_up_ps"])
            s0 = sync_start("fall" if r["edge_fall"] else "rise", T)
            m = math.ceil((s0 - d) / T)               # sync physics: the first sampling edge at/after arrival
            nn[x] = nn[r["parent"]] + m + SYNC - 1 - LAUNCH + r["pad"]
        for pid, c in ports.items():
            row = rows_by_port[pid]
            w = wander_frac * max(row.get("unshared_a_ps", 0.0), row.get("unshared_b_ps", 0.0))
            if c["tree"]:
                # the tree crossing's own lag: the phase it was synchronised at (drawn above), then wander after start
                L = (c["K"] + nn[c["dst"]] - nn[c["src"]]) * T + dtree[c["dst"]] + rnd.uniform(-w, w)
            else:
                # any time after start: the derated interval already holds every operating phase of this crossing;
                # only the origins were frozen at start (tree phases above)
                d = rnd.uniform(row["d_ps"] - row["p_dn_ps"], row["d_ps"] + row["p_up_ps"])
                L = (c["K"] + nn[c["dst"]] - nn[c["src"]]) * T + d
            hi_edge = (c["depth"] - 0.5) * T - ap
            ml, mh = L - lo_edge, hi_edge - L
            if ml < worst_lo:
                worst_lo, worst["lo"] = ml, pid
            if mh < worst_hi:
                worst_hi, worst["hi"] = mh, pid
            if ml < 0 or mh < 0:
                bad += 1
    return dict(identity_and_loop_errors=errs, fundamental_cycles=len(loops), samples=samples,
                sim_window_violations=bad, sim_min_margin_low_ps=round(worst_lo, 1),
                sim_min_margin_high_ps=round(worst_hi, 1), sim_worst_ports=worst,
                note="margins are to the ring window edges that already keep ap = T/8 inside; the COORD 20:35 "
                     "definition adds ap to the margin: gate margin = sim margin + ap")


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
    t["count_aligned"] = dict(schema=b["schema"], period_ps=b["period_ps"], root=b["root"], pad=b["pad"],
                              root_settle_cycles=root_settle_cycles,
                              ports={pid: {k: c[k] for k in ("K", "depth", "sched_lat", "tree")}
                                     for pid, c in b["ports"].items() if any(r["port"] == pid for r in t["ports"])},
                              regions={k: {x: v[x] for x in ("parent", "tree_port", "edge_fall", "pad")}
                                       for k, v in b["regions"].items()})
    return t


def lane_cycles(table):
    """{lane: added landing cycles} with per-crossing count-aligned latency (or the old +3)"""
    out = defaultdict(int)
    for r in table["ports"]:
        out[r.get("lane")] += int(r.get("added_cycles", 3))
    return dict(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ocv_json")
    ap.add_argument("--corner", default="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5")
    ap.add_argument("--period", type=float, default=833.0)
    ap.add_argument("--aperture", type=float, default=833.0 / 8)
    ap.add_argument("--wander-frac", type=float, default=0.05)
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--table")
    ap.add_argument("--table-out")
    ap.add_argument("--root-settle", type=int, default=64)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    d = json.load(open(a.ocv_json))
    rows = CAP.joint_rows(d, a.corner.split(","))
    summ, out = CAP.plan([dict(r) for r in rows], a.period, a.aperture, a.wander_frac)
    b = bind(summ, out, a.period, a.pad)
    v = verify(b, {r["port"]: r for r in rows}, a.samples, a.aperture, a.wander_frac)
    summ.pop("_tree")
    hist = defaultdict(int)
    for c in b["ports"].values():
        hist[c["sched_lat"]] += 1
    rep = dict(plan=summ, verify=v, sched_lat_hist=dict(sorted(hist.items())),
               sched_lat_total=sum(c["sched_lat"] for c in b["ports"].values()),
               old_ring_total=3 * len(b["ports"]),
               K_range=[min(c["K"] for c in b["ports"].values()), max(c["K"] for c in b["ports"].values())],
               start_tree_depth=max(r["depth"] for r in b["regions"].values()),
               max_origin_cycles=max(r["n_nominal"] for r in b["regions"].values()))
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
