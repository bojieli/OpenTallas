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
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_plan as CAP  # noqa: E402

SYNC = 3    # ot_dp_landing_origin synchroniser flops (s0, s1, s2); the fall form adds a negedge stage (in s below)
LAUNCH = 1  # the forwarded start is the parent origin's REGISTER output: it rises one parent edge before word 0
# Intra-region start relay (DIE-KV-3/CAORIGIN, COORD 21:14 ASK 3): tx flop in the origin partition + rx flop in the
# relay partition, both ot_dp_landing_relay on the region clock (rtl/common/ot_dp_clk_landing_ca.sv).  A relay
# partition starts RELAY_STAGES counts after its region origin.
RELAY_STAGES = 2


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


def bind(plan, T=None, parts=None):
    """plan = count_align_plan.py --out document {summary, regions, crossings}.
    parts (opt-in, DIE-KV-3/CAORIGIN): {port: (src_partition, dst_partition)}; None = one origin per region (output
    unchanged).  With parts a region holding several landed partitions gets ONE origin partition and a timed start
    relay to the others (bind_parts); the plan's origins/latency/lag are unchanged, only non-tree RTL K moves."""
    summ, regs, xs = plan["summary"], plan["regions"], plan["crossings"]
    T = float(summ.get("period_ps", 833.0) if T is None else T)
    if summ.get("regions_reached") != summ.get("regions"):
        raise BindError(f"start tree not spanning: {summ.get('regions_reached')} of {summ.get('regions')} regions")
    bad = [o["port"] for o in xs if not o.get("rtl")]
    if bad:
        raise BindError(f"{len(bad)} crossings have no RTL K/DEPTH (plan FAIL/unreached): {bad[:5]}")
    rows = {o["port"]: o for o in xs}
    # START-TREE-1 (--start-tree clock): dedicated start ports (not data crossings) carry the start tree
    starts = {e["port"]: e for e in plan.get("start_edges", [])}
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
        o = rows.get(port, starts.get(port))
        if o is None:
            raise BindError(f"tree port {port}: neither a crossing nor a start port of the plan")
        if (o["src"], o["dst"]) != (p, x):
            raise BindError(f"tree port {port} is not parent {p} -> child {x} (start rides src -> dst only)")
        step = n[x] - n[p]
        if step != e["offset_from_parent"]:
            raise BindError(f"tree edge {port}: origin step {step} != plan offset_from_parent {e['offset_from_parent']}")
        # convention equality on the nominal phase and on both ends of the plan's J deviation interval
        sd = e.get("sample_d_ps", o["d_ps"])     # FLOW-ONEMODEL-1: the sampled phase (measured fall for a fall sample)
        a = integ_step(sd, e["edge"], T, pad)
        b = count2_step(sd, e["edge"], T, pad)
        if not (a == b == step):
            raise BindError(f"tree edge {port}: MESO-INTEG-1 step {a} / MESO-COUNT-2 step {b} / plan {step} differ")
        regions[x] = dict(parent=p, tree_port=port, edge_fall=bool(e["rtl"]["EDGE_FALL"]), pad=pad, n_nominal=n[x],
                          depth=int(g["tree_depth"]), sync_values=int(e["sync_values"]),
                          sync_dist_ps=e["sync_dist_ps"], start_skew_limit_ps=e.get("start_skew_limit_ps"))
        if "sample_interval_ps" in e:
            regions[x]["sample_lo_ps"], regions[x]["sample_hi_ps"] = e["sample_interval_ps"]
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
        if o.get("src_part") is not None:
            # FLOW-ONEMODEL-1: the partition pair the plan timed this port on (die_sta_related times it on the same)
            ports[o["port"]].update(src_part=o["src_part"], dst_part=o["dst_part"])
    b = dict(schema="opentallas.count_align_bind.v2", form="count_aligned", period_ps=T,
                pad=int(summ.get("pad", 0)), root=root[0], ports=ports, regions=regions,
                sync_aperture_ps=summ.get("sync_aperture_ps", 26.5), aperture_ps=summ.get("aperture_ps", T / 8),
                start_skew_limit_min_ps=summ.get("start_skew_limit_min_ps"),
                convention="a_child - a_parent = PAD + 2 + J(d) = MESO-INTEG-1 m + 1 + PAD (identity, checked per edge); "
                           "RTL K = plan K_eff - n0",
                latency_frame="receiver counts; sched_lat = K + 1 + n_dst - n_src (nominal) = plan lat_cycles")
    if starts:
        for g in regs:
            regions[g["region"]]["virtual"] = bool(g.get("virtual"))
    if starts:
        # START-TREE-1: the start ports, their tap ends and the derated start interval (verify() samples it; the die STA
        # re-checks it on built arrivals); step = PAD + 2 + J (sender -> child origin), K + 1 = 0 in the loop identity
        b["start_tree"] = "clock"
        b["start_ports"] = {pid: dict(src=e["src"], dst=e["dst"], d_ps=e["d_ps"],
                                      d_lo_ps=round(e["d_ps"] - e["p_dn_ps"], 1), d_hi_ps=round(e["d_ps"] + e["p_up_ps"], 1),
                                      step=regions[e["dst"]]["n_nominal"] - regions[e["src"]]["n_nominal"],
                                      **{k: e.get(k) for k in ("launch", "capture", "launch_part", "capture_part",
                                                               "retime", "fork_node")})
                            for pid, e in starts.items()}
    if summ.get("start_skew_clean"):
        # MESO-START-2 (opt-in): the start-up sim samples each tree edge at d - skew (plan --start-skew-clean)
        b["start_skew_ps"] = [float(x) for x in summ["start_skew_ps"]]
    return b if parts is None else bind_parts(b, parts)


def bind_parts(b, parts):
    """Intra-region start relay (DIE-KV-3/CAORIGIN 69d1ba8933 on the plan-param bind v2; COORD 21:14 ASK 3).

    ORIGIN CHOICE (deterministic): a child region's origin is the partition that receives its start-tree port; the root
    region's origin is the partition that sends the most child-region tree ports, then the most landed crossings, then
    the first by name.  Every other landed partition of the region is a RELAY: origin start -> RELAY_STAGES registers of
    the region clock (ot_dp_landing_relay tx -> cland_rstart pin -> rx): a same-clock registered ctl path timed by the die
    STA as an intra-region pair, not a landed crossing.
    COUNT FRAMES: N(root origin) = 0; N(origin of child x on tree port s->o_x) = N(sender partition of s) + plan step
    (PAD_e + 2 + J, unchanged by a relayed sender); N(relay q) = N(region origin) + r.  Lag L = (K + N_d - N_s) T + d
    keeps the plan's value, so tree K = plan K and non-tree K = sched_lat - 1 - (N_d - N_s); sched_lat unchanged.
    LOOPS over the partition tree (relay edge: sched_lat r, K + 1 = 0) are checked by verify()."""
    reg, ports = b["regions"], b["ports"]
    reg_parts = defaultdict(set)
    for pid, c in ports.items():
        if pid not in parts:
            raise BindError(f"crossing {pid}: no partition endpoints")
        sp, dp = parts[pid]
        reg_parts[c["src"]].add(sp)
        reg_parts[c["dst"]].add(dp)
    sp_ = b.get("start_ports", {})
    for pid, c in sp_.items():
        # START-TREE-1: the start launch flop sits in the fork tap's partition, the sync in the capture tap's; a
        # virtual (clock-tree node) start node is its own frame
        for x, q in ((c["src"], c["launch_part"]), (c["dst"], c["capture_part"])):
            reg_parts[x].add(q if (q and not reg[x].get("virtual")) else x)
    owner = {}
    for r, ps in reg_parts.items():
        for pn in ps:
            if owner.setdefault(pn, r) != r:
                raise BindError(f"partition {pn} lands in two regions ({owner[pn]}, {r})")
    tree_ports = {r["tree_port"] for r in reg.values() if r["tree_port"]}
    sends, nports = defaultdict(int), defaultdict(int)
    def eparts(port):
        if port in sp_:
            c = sp_[port]
            return (c["launch_part"] if c["launch_part"] and not reg[c["src"]].get("virtual") else c["src"],
                    c["capture_part"] if c["capture_part"] and not reg[c["dst"]].get("virtual") else c["dst"])
        return parts[port]
    for port in tree_ports:
        sends[eparts(port)[0]] += 1
    for pid in ports:
        sp, dp = parts[pid]
        nports[sp] += 1
        nports[dp] += 1
    root = b["root"]
    origin = {x: eparts(r["tree_port"])[1] for x, r in reg.items() if r["tree_port"]}
    origin[root] = min(reg_parts[root], key=lambda q: (-sends[q], -nports[q], q))
    N, pinfo = {origin[root]: 0}, {}

    def relays(x):
        for q in sorted(reg_parts[x] - {origin[x]}):
            N[q] = N[origin[x]] + RELAY_STAGES
            pinfo[q] = dict(region=x, role="relay", src=origin[x], stages=RELAY_STAGES, n_nominal=N[q])
        pinfo[origin[x]] = dict(region=x, role="origin", src=None, stages=0, n_nominal=N[origin[x]])
    relays(root)
    for x in sorted((x for x in reg if reg[x]["parent"] is not None), key=lambda x: reg[x]["depth"]):
        r = reg[x]
        step = r["n_nominal"] - reg[r["parent"]]["n_nominal"]
        N[origin[x]] = N[eparts(r["tree_port"])[0]] + step
        relays(x)
    for pid, c in ports.items():
        sp, dp = parts[pid]
        if not c["tree"]:
            c["K"] = c["sched_lat"] - 1 - (N[dp] - N[sp])
        c.update(src_part=sp, dst_part=dp)
    for pid, c in sp_.items():
        c["src_part"], c["dst_part"] = eparts(pid)
    for x, r in reg.items():
        r["origin_part"] = origin[x]
        r["n_region_frame"] = r["n_nominal"]
        r["n_nominal"] = N[origin[x]]
    b.update(parts=dict(sorted(pinfo.items())), relay_stages=RELAY_STAGES,
             latency_frame="receiver PARTITION counts; sched_lat = K + 1 + N_dst - N_src (nominal) = plan lat_cycles; "
                           "relay partition N = origin N + relay_stages")
    return b


def _start_tree(b):
    """node -> (parent node, edge id) of the start spanning tree; nodes are regions, or partitions when the bind has
    relays (edge id 'relay:<partition>' for an intra-region relay)"""
    reg = b["regions"]
    if "parts" not in b:
        return {x: (r["parent"], r["tree_port"]) for x, r in reg.items()}
    up = {}
    for q, pi in b["parts"].items():
        if pi["role"] == "relay":
            up[q] = (pi["src"], "relay:" + q)
        elif reg[pi["region"]]["parent"] is None:
            up[q] = (None, None)
        else:
            tp = reg[pi["region"]]["tree_port"]
            up[q] = ((b["ports"].get(tp) or b["start_ports"][tp])["src_part"], tp)
    return up


def _ends(b, c):
    return (c["src_part"], c["dst_part"]) if "parts" in b else (c["src"], c["dst"])


def _edge(b, eid):
    """(sched_lat, K + 1) of a start-tree edge or crossing; a relay edge is r stages with K + 1 = 0"""
    if eid.startswith("relay:"):
        return b["parts"][eid[6:]]["stages"], 0
    if eid in b.get("start_ports", {}):
        return b["start_ports"][eid]["step"], 0     # START-TREE-1 start port: origin step, no ring
    c = b["ports"][eid]
    return c["sched_lat"], c["K"] + 1


def fundamental_cycles(b):
    """one loop per non-tree crossing: the crossing plus the tree path back; returns [(edge id, +1/-1 orientation)]"""
    upm = _start_tree(b)

    def up(x):
        path = []
        while upm[x][0] is not None:
            path.append(x)
            x = upm[x][0]
        return path + [x]
    cyc = []
    for pid, c in b["ports"].items():
        if c["tree"]:
            continue
        s, d = _ends(b, c)
        pu, pv = up(s), up(d)
        common = next(x for x in pu if x in set(pv))
        loop = [(pid, +1)]
        for x in pv[:pv.index(common)]:
            loop.append((upm[x][1], -1))
        for x in reversed(pu[:pu.index(common)]):
            loop.append((upm[x][1], +1))
        cyc.append(loop)
    return cyc


def verify(b, samples=2000, seed=1, need_ps=100.0):
    T = b["period_ps"]
    sap = float(b.get("sync_aperture_ps", 26.5))
    reg, ports = b["regions"], b["ports"]
    errs = []
    nom = b["parts"] if "parts" in b else reg
    for pid, c in ports.items():
        s_, d_ = _ends(b, c)
        lhs = c["K"] + 1 + nom[d_]["n_nominal"] - nom[s_]["n_nominal"]
        if lhs != c["sched_lat"]:
            errs.append(f"identity {pid}: K+1+dn {lhs} != sched_lat {c['sched_lat']}")
    for q, pi in b.get("parts", {}).items():
        if pi["role"] == "relay" and pi["n_nominal"] != nom[pi["src"]]["n_nominal"] + pi["stages"]:
            errs.append(f"relay {q}: N {pi['n_nominal']} != origin N + {pi['stages']}")
    loops = fundamental_cycles(b)
    for lp in loops:
        s1 = sum(sg * _edge(b, p)[0] for p, sg in lp)
        s2 = sum(sg * _edge(b, p)[1] for p, sg in lp)
        if s1 != s2:
            errs.append(f"loop {lp[0][0]}: sum sched_lat {s1} != sum(K+1) {s2}")
    rnd = random.Random(seed)
    order = sorted(reg, key=lambda x: reg[x]["depth"])
    worst_lo, worst_hi, bad, worst = math.inf, math.inf, 0, {}
    relay_of = defaultdict(list)
    for q, pi in b.get("parts", {}).items():
        if pi["role"] == "relay":
            relay_of[pi["region"]].append(q)
    org = {x: r.get("origin_part", x) for x, r in reg.items()}
    for i in range(samples):
        mode = i % 3       # 0 uniform, 1 / 2 interval endpoints (mixed)
        dd = {}
        for pid, c in ports.items():
            lo, hi = c["d_lo_ps"], c["d_hi_ps"]
            x = rnd.uniform(lo, hi) if mode == 0 else rnd.choice((lo, hi))
            dd[pid] = x + c["wander_ps"] * rnd.uniform(-1, 1)
        for pid, c in b.get("start_ports", {}).items():
            lo, hi = c["d_lo_ps"], c["d_hi_ps"]
            dd[pid] = rnd.uniform(lo, hi) if mode == 0 else rnd.choice((lo, hi))
        nn = {}
        for x in order:
            r = reg[x]
            if r["parent"] is None:
                nn[org[x]] = 0
                for q in relay_of[x]:
                    nn[q] = b["parts"][q]["stages"]      # registered same-clock relay: exact
                continue
            c = ports.get(r["tree_port"]) or b["start_ports"][r["tree_port"]]
            # the start was synchronised at a phase inside the derated interval (no post-start wander yet)
            d0 = min(max(dd[r["tree_port"]], c["d_lo_ps"]), c["d_hi_ps"])
            if "sample_lo_ps" in r:
                # FLOW-ONEMODEL-1: the sync samples its own (measured fall / rise) interval
                slo, shi = r["sample_lo_ps"], r["sample_hi_ps"]
                d0 = rnd.uniform(slo, shi) if mode == 0 else rnd.choice((slo, shi))
            if "start_skew_ps" in b:
                sk = b["start_skew_ps"]
                d0 -= rnd.uniform(*sk) if mode == 0 else rnd.choice(sk)   # the sync samples d - skew
            edge = "fall" if r["edge_fall"] else "rise"
            s = sync_start(edge, T)
            ph = (d0 - s) % T                      # distance past the last sampling boundary
            m = math.ceil((s - d0) / T)
            if ph < sap and rnd.random() < 0.5:
                m += 1                             # metastable just after the boundary: resolved late
            elif ph > T - sap and rnd.random() < 0.5:
                m -= 1                             # metastable just before: resolved early
            snd = _ends(b, c)[0]                   # the tree port's sender (a relay partition starts r late)
            nn[org[x]] = nn[snd] + m + SYNC - 1 - LAUNCH + r["pad"]
            for q in relay_of[x]:
                nn[q] = nn[org[x]] + b["parts"][q]["stages"]
        for pid, c in ports.items():
            s_, d_ = _ends(b, c)
            L = (c["K"] + nn[d_] - nn[s_]) * T + dd[pid]
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


def annotate_table(table, b, root_settle_cycles=64, strap_form=False):
    """clock_landings / fallback_land region table -> count-aligned form (opt-in; the old ring stays the default).
    strap_form (MESO-STRAP-1, OWNER 12.15a, opt-in): clock_landings emits the strap form (strap_ca_* pins, one design
    per type, parent ties from strap_ties())."""
    t = json.loads(json.dumps(table))
    miss = [r["port"] for r in t["ports"] if r["port"] not in b["ports"]]
    if miss:
        raise BindError(f"{len(miss)} table crossings missing from the bind: {miss[:5]}")
    for r in t["ports"]:
        c = b["ports"][r["port"]]
        if (c["src"], c["dst"]) != (r["src_region"], r["dst_region"]):
            raise BindError(f"{r['port']}: bind regions {c['src']}->{c['dst']} != table {r['src_region']}->{r['dst_region']}")
        if "parts" in b and (c["src_part"], c["dst_part"]) != (r["src"], r["dst"]):
            raise BindError(f"{r['port']}: bind partitions {c['src_part']}->{c['dst_part']} != table {r['src']}->{r['dst']}")
        r["added_cycles"] = c["sched_lat"]
    tp = {r["port"] for r in t["ports"]}
    t["count_aligned"] = dict(schema=b["schema"], period_ps=b["period_ps"], root=b["root"], pad=b["pad"],
                              root_settle_cycles=root_settle_cycles,
                              ports={pid: {k: c[k] for k in ("K", "depth", "sched_lat", "tree")}
                                     for pid, c in b["ports"].items() if pid in tp},
                              regions={k: {x: v[x] for x in ("parent", "tree_port", "edge_fall", "pad", "origin_part")
                                           if x in v}
                                       for k, v in b["regions"].items()})
    if strap_form:
        t["count_aligned"]["strap_form"] = True
    if b.get("start_ports"):
        # START-TREE compose slice: the start ports (dedicated start pins / die-level stages) travel with the table
        t["count_aligned"]["start_tree"] = b.get("start_tree", "clock")
        t["count_aligned"]["start_ports"] = {pid: {k: c.get(k) for k in ("src", "dst", "launch_part", "capture_part",
                                                                          "src_part", "dst_part")}
                                             for pid, c in sorted(b["start_ports"].items())}
    if "parts" in b:
        t["count_aligned"]["parts"] = {q: {x: v[x] for x in ("region", "role", "src", "stages")}
                                       for q, v in b["parts"].items()}
        t["count_aligned"]["relay_stages"] = b["relay_stages"]
    return t


# MESO-STRAP-1 (OWNER 12.15a COUNT STRAPS; METHODOLOGY 1.8 conditions).  Strap form: every copy of a partition type
# shares one hardened design; the count-aligned constants that differ between copies are strap_* INPUT pins tied at the
# parent (TIEHI/TIELO per bit), the ring DEPTH is the type's largest.  Pins (per receiving type):
#   strap_ca_k_<bus>[KW-1:0]  ring read offset K mod 2^KW, KW = log2(DEPTH) + 4 (ot_dp_clk_landing_cas strap_k)
#   strap_ca_pad[PADW-1:0], strap_ca_efall   child origin PAD / EDGE_FALL (ot_dp_landing_origin_s), child-capable types
#   strap_ca_tsel[TSW-1:0]  which landed input carries the parent's forwarded start (only if it differs between copies)
#   strap_ca_root           root origin (ot_dp_landing_root) instead of a child origin (only if both occur in the type)
# Copies that differ in the intra-region RELAY role (rx relay vs origin, or tx relay out present vs absent) change the
# type's pin list (cland_rstart_in / cland_rstart_out) and stay a TYPE_SPLIT (residual_split; never an open/tied input).
STRAP_PREFIX = "strap_ca_"


def strap_kw(depth):
    """strap width of a ring K: the ring's count width log2(DEPTH) + 1 + LAPX(3)"""
    return int(depth).bit_length() - 1 + 4


def strap_bits(value, width):
    """K (any integer) -> its width-bit two's-complement pattern as an int (K mod 2^width)"""
    return int(value) % (1 << int(width))


def reader_start_depth(plan, tn):
    """Optional uniform ring-reader START transport; logical origin is unchanged."""
    cfg = plan["partition_types"][tn].get("clock", {}).get("landing_reader_start")
    if cfg is None:
        return 0
    if not isinstance(cfg, dict):
        raise BindError(f"{tn}: landing_reader_start must be an object")
    depth = cfg.get("depth")
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
        raise BindError(f"{tn}: landing_reader_start.depth must be an integer >= 1")
    return depth


def writer_start_depth(plan, tn, bus=None):
    """Optional forwarded-writer START transport (W1, DIE-HEAD-38): W registered stages between the sender's safe
    start_d and its FSTART face flop on the listed output buses only. bus=None -> the declared W (0 if absent)."""
    cfg = plan["partition_types"][tn].get("clock", {}).get("landing_writer_start")
    if cfg is None:
        return 0
    if not isinstance(cfg, dict):
        raise BindError(f"{tn}: landing_writer_start must be an object")
    depth = cfg.get("depth")
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
        raise BindError(f"{tn}: landing_writer_start.depth must be an integer >= 1")
    if bus is None:
        return depth
    return depth if bus in cfg.get("branches", {}) else 0


# START-TREE compose slice (DIE-HEAD-11, opt-in by a bind with start_tree="clock"): a child region's start no longer rides
# a landed data crossing; it arrives on ONE dedicated start pin of its origin partition (cland_tstart_in), launched
# from the parent origin partition's cland_tstart_out (= its cland_start, one pin per partition, fanned out at the die
# top) or from a die-level start stage (tools/die_plan/start_stage_emit.py nets rs_<region> / pst_<region>).
START_PIN_IN = "cland_tstart_in"
START_PIN_OUT = "cland_tstart_out"


def start_port_end(ca, tree_port):
    """START-TREE start port -> (capture partition, the start pin) or None for a landed data crossing tree port"""
    sp = (ca.get("start_ports") or {}).get(tree_port)
    if sp is None:
        return None
    return sp.get("dst_part") or sp.get("capture_part"), START_PIN_IN


def strap_ties(ca, plan):
    """count-aligned bind table (annotate_table()["count_aligned"]) + die plan -> per-type strap declarations and the
    per-instance tie VALUES (the single source the parent ties, the tie-value audit and the LEC variants use).
    -> dict(schema, types={type: dict(buses={bus: dict(depth, kw)}, origin, straps={port: width}, variants,
            residual_split)}, instances={part: dict(type, values={port: int}, role, variant)}, summary)"""
    ports = {p["id"]: p for p in plan["ports"]}
    ptype = {p["name"]: p["type"] for p in plan["partitions"]}
    inst_bus = defaultdict(dict)
    for pid, c in ca["ports"].items():
        p = ports.get(pid)
        if p is None:
            raise BindError(f"strap ties: bind crossing {pid} has no plan port")
        q, bus = p["dst"]["part"], p["dst"]["bus"]
        if bus in inst_bus[q]:
            raise BindError(f"strap ties: two count-aligned crossings land on {q}.{bus}")
        # Only the reader count starts R edges later.  c_new-K_new equals
        # c_old-K_old exactly when K_new=K_old-R (modulo the ring count width).
        # A sender writer START delayed W edges (landing_writer_start) writes W edges later: K_new=K_old+W-R
        # (W1/R proof results/die_head_36_1029/writer_r1_proof, 4572 cases).
        s = p["src"]
        inst_bus[q][bus] = dict(K=int(c["K"]) - reader_start_depth(plan, ptype[q])
                                + writer_start_depth(plan, ptype[s["part"]], s["bus"]),
                               depth=int(c["depth"]), port=pid, tree=bool(c["tree"]))
    cparts = ca.get("parts")
    role = {}
    landed = set(inst_bus) | {ports[pid]["src"]["part"] for pid in ca["ports"]}
    for q in sorted(landed):
        if cparts is not None:
            pi = cparts.get(q)
            if pi is None:
                raise BindError(f"strap ties: landed partition {q} has no bind role")
            reg_name, kind = pi["region"], pi["role"]
        else:
            regs = [x for x, r in ca["regions"].items() if r.get("origin_part", None) == q]
            reg_name = regs[0] if regs else None
            kind = "origin"
            if reg_name is None:   # one partition per region (MESO-INTEG-1): the tree port's receiver / root sender
                reg_name = next((x for x, r in ca["regions"].items() if r["tree_port"]
                                 and (start_port_end(ca, r["tree_port"]) or (ports[r["tree_port"]]["dst"]["part"],))[0]
                                 == q), None)
                if reg_name is None:
                    reg_name = ca["root"]
        tx = cparts is not None and kind == "origin" and any(v["role"] == "relay" and v["src"] == q
                                                              for v in cparts.values())
        if kind == "relay":
            role[q] = dict(kind="relay", tx=False)
            continue
        r = ca["regions"][reg_name]
        if r["parent"] is None:
            role[q] = dict(kind="root", tx=tx)
        else:
            se = start_port_end(ca, r["tree_port"])
            if se is None:
                tp = ports[r["tree_port"]]
                se = (tp["dst"]["part"], tp["dst"]["bus"])
            if se[0] != q:
                raise BindError(f"strap ties: region {reg_name} tree port {r['tree_port']} lands on "
                                f"{se[0]}, not its origin {q}")
            role[q] = dict(kind="child", tx=tx, tree_bus=se[1], pad=int(r["pad"]),
                           edge_fall=bool(r["edge_fall"]))
    by_type = defaultdict(list)
    for q in landed:
        by_type[ptype[q]].append(q)
    types, insts = {}, {}
    for tn, qs in sorted(by_type.items()):
        qs.sort()
        buses = sorted({b for q in qs for b in inst_bus.get(q, {})})
        miss = [(q, b) for q in qs for b in buses if b not in inst_bus.get(q, {})]
        if miss:
            raise BindError(f"strap ties: type {tn} copies land different buses (landing mask split first): {miss[:3]}")
        depth = {b: max(inst_bus[q][b]["depth"] for q in qs) for b in buses}
        straps = {f"{STRAP_PREFIX}k_{b}": strap_kw(depth[b]) for b in buses}
        # origin class: relay rx / origin with or without tx relay -> a pin-list difference -> residual split
        cls = {q: (role[q]["kind"] == "relay", role[q]["tx"]) for q in qs}
        kinds = {role[q]["kind"] for q in qs}
        org = sorted(q for q in qs if role[q]["kind"] in ("root", "child"))
        tsel = sorted({role[q]["tree_bus"] for q in org if role[q]["kind"] == "child"})
        has_child = any(role[q]["kind"] == "child" for q in org)
        origin = dict(form="none" if not org else "root" if not has_child else "strap", tree_buses=tsel,
                      root=("root" in kinds) and has_child, relay_rx="relay" in kinds,
                      relay_tx=any(role[q]["tx"] for q in qs))
        if has_child:
            padmax = max(role[q]["pad"] for q in org if role[q]["kind"] == "child")
            origin["padw"] = max(1, int(padmax).bit_length())
            straps[f"{STRAP_PREFIX}pad"] = origin["padw"]
            straps[f"{STRAP_PREFIX}efall"] = 1
            if len(tsel) > 1:
                origin["tsw"] = (len(tsel) - 1).bit_length()
                straps[f"{STRAP_PREFIX}tsel"] = origin["tsw"]
            if origin["root"]:
                straps[f"{STRAP_PREFIX}root"] = 1
        variants = {}
        for q in qs:
            v = {f"{STRAP_PREFIX}k_{b}": strap_bits(inst_bus[q][b]["K"], straps[f"{STRAP_PREFIX}k_{b}"]) for b in buses}
            rq = role[q]
            if has_child and rq["kind"] in ("root", "child"):
                ch = rq["kind"] == "child"
                v[f"{STRAP_PREFIX}pad"] = rq["pad"] if ch else 0
                v[f"{STRAP_PREFIX}efall"] = int(rq["edge_fall"]) if ch else 0
                if "tsw" in origin:
                    v[f"{STRAP_PREFIX}tsel"] = tsel.index(rq["tree_bus"]) if ch else 0
                if origin["root"]:
                    v[f"{STRAP_PREFIX}root"] = int(not ch)
            elif has_child:     # relay copy of a child-capable type (residual split): origin straps unused -> 0
                v.update({k: 0 for k in straps if not k.startswith(f"{STRAP_PREFIX}k_")})
            key = json.dumps([cls[q], sorted(v.items())])
            vi = variants.setdefault(key, len(variants))
            insts[q] = dict(type=tn, values=v, role=dict(rq), variant=vi,
                            K={b: inst_bus[q][b]["K"] for b in buses})
        classes = sorted({cls[q] for q in qs})
        types[tn] = dict(instances=qs, buses={b: dict(depth=depth[b], kw=straps[f"{STRAP_PREFIX}k_{b}"]) for b in buses},
                         origin=origin, straps=straps, strap_bits=sum(straps.values()), variants=len(variants),
                         residual_split=[dict(relay_rx=a, relay_tx=b_, instances=[q for q in qs if cls[q] == (a, b_)])
                                         for a, b_ in classes] if len(classes) > 1 else [])
    summ = dict(types=len(types), instances=len(insts), lec_variants=sum(t["variants"] for t in types.values()),
                tied_strap_bits=sum(t["strap_bits"] * len(t["instances"]) for t in types.values()),
                residual_split_types=sum(1 for t in types.values() if t["residual_split"]),
                types_after_straps=sum(max(1, len(t["residual_split"])) for t in types.values()),
                d8_type_buses=sum(1 for t in types.values() for b in t["buses"].values() if b["depth"] == 8),
                types_with_tsel=sum(1 for t in types.values() if "tsw" in t["origin"]),
                types_with_root_strap=sum(1 for t in types.values() if t["origin"].get("root")))
    return dict(schema="opentallas.count_straps.v1", rule="OWNER 12.15a count straps (METHODOLOGY 1.8 conditions)",
                types=types, instances=dict(sorted(insts.items())), summary=summ)


def table_parts(table):
    """{port: (src partition, dst partition)} from a clock_landings regions table"""
    return {r["port"]: (r["src"], r["dst"]) for r in table["ports"]}


def relay_summary(b):
    """regions with several landed partitions, relay pins, and the relay shift of K on the crossings"""
    if "parts" not in b:
        return dict(multi_partition_regions=0, relay_partitions=0)
    per = defaultdict(int)
    for q, v in b["parts"].items():
        per[v["region"]] += 1
    rel = {q for q, v in b["parts"].items() if v["role"] == "relay"}
    shifted = [p for p, c in b["ports"].items() if not c["tree"] and (c["src_part"] in rel) != (c["dst_part"] in rel)]
    return dict(landed_regions=len(per), multi_partition_regions=sum(1 for v in per.values() if v > 1),
                partitions_per_region_hist=dict(sorted(Counter(per.values()).items())),
                relay_partitions=len(rel), relay_pins=dict(tx_out=sum(1 for v in per.values() if v > 1), rx_in=len(rel)),
                relay_stages=b["relay_stages"],
                crossings_with_relayed_receiver=sum(1 for c in b["ports"].values() if c["dst_part"] in rel),
                crossings_with_relayed_sender=sum(1 for c in b["ports"].values() if c["src_part"] in rel),
                tree_ports_from_relay_sender=sum(1 for c in b["ports"].values() if c["tree"] and c["src_part"] in rel),
                nontree_K_shifted_by_relay=len(shifted))


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
                depth_hist={str(k): sum(1 for c in b["ports"].values() if c["depth"] == k) for k in (4, 8, 16)},
                K_range=[min(c["K"] for c in b["ports"].values()), max(c["K"] for c in b["ports"].values())],
                start_tree_depth=max(r["depth"] for r in b["regions"].values()),
                tree_edges_fall=sum(1 for r in b["regions"].values() if r["edge_fall"]),
                max_origin_cycles=max(r["n_nominal"] for r in b["regions"].values()))


def ocv_parts(rows):
    """--parts ocv: {port: (src partition, dst partition)} from the OCV rows.  A row without src_part/dst_part is a
    partition-level row (its src/dst ARE partitions, e.g. tools/s81_head/landed_phase_ocv.py), so the partition is the
    row's src/dst -- the same identity fallback count_align_plan.row_ports() uses for the plan and the STA intervals
    (DIE-S81-17: the bind raised KeyError 'src_part' on every S81 --parts ocv run, go12..go15).
    FAIL-CLOSED (S81-LP-1): a row with no partition identity at all (neither src_part/dst_part nor src/dst), or a port
    whose rows (one per corner) disagree on its partition pair, raises BindError naming the port -- never a bare
    KeyError and never a silent last-row-wins pick."""
    out = {}
    for r in rows:
        pid = r.get("port")
        ends = tuple(r.get(k + "_part") if r.get(k + "_part") is not None else r.get(k) for k in ("src", "dst"))
        if pid is None or any(e is None or e == "" for e in ends):
            raise BindError(f"--parts ocv: row {pid!r} has no src/dst partition (needs src_part/dst_part or src/dst)")
        if out.setdefault(pid, ends) != ends:
            raise BindError(f"--parts ocv: port {pid} rows disagree on partitions {out[pid]} vs {ends}")
    return out


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
    ap.add_argument("--start-skew", type=CAP.parse_skew, default=(0.0, 0.0), metavar="LO,HI",
                    help="count_align_plan.py --start-skew (with --from-ocv)")
    ap.add_argument("--start-skew-clean", action="store_true",
                    help="count_align_plan.py --start-skew-clean (with --from-ocv); the start-up sim then samples d - skew")
    ap.add_argument("--tree-parent", action="append", metavar="REGION=PORT",
                    help="count_align_plan.py --tree-parent (with --from-ocv)")
    ap.add_argument("--sta-proof", metavar="DIR", help="count_align_plan.py --sta-proof (with --from-ocv)")
    ap.add_argument("--sta-plan", help="count_align_plan.py --sta-plan (with --from-ocv)")
    ap.add_argument("--sta-clock-cal", choices=("none", "spice", "spice_edge", "spice_buf_edge", "spice_cell"),
                    default=None, help="legacy default spice; ignored under --margin-policy nominal (OWNER 12.24b)")
    ap.add_argument("--sta-cppr-lca", action="store_true")
    CAP.add_sta_ocv_args(ap)
    CAP.add_start_tree_args(ap)
    ap.add_argument("--samples", type=int, default=2000)
    ap.add_argument("--table")
    ap.add_argument("--table-out")
    ap.add_argument("--root-settle", type=int, default=64)
    ap.add_argument("--parts", choices=("auto", "region", "table", "ocv"), default="auto",
                    help="count frames: region = one origin per region; table / ocv = per partition with intra-region "
                         "start relays (DIE-KV-3/CAORIGIN), endpoints from the regions table / the OCV rows' "
                         "src_part,dst_part (with --from-ocv); auto = table when --table is given, else region")
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan-die", help="MESO-STRAP-1: die plan (partitions/ports) for --straps-out")
    ap.add_argument("--strap-form", action="store_true", help="MESO-STRAP-1: mark the --table-out for the strap form")
    ap.add_argument("--straps-out", help="MESO-STRAP-1 (OWNER 12.15a): write per-type strap pins + per-instance tie "
                    "values (count_straps.v1) for the annotated table (needs --table and --plan-die)")
    a = ap.parse_args(argv)
    mpol = CAP.apply_sta_margin_policy(a)      # OWNER 12.24b, before any check that reads a margin flag
    CAP.check_start_tree_args(a, ap.error)
    if a.start_tree == "clock" and not a.from_ocv:
        ap.error("--start-tree clock plans in-process: needs --from-ocv (a plan JSON carries its own start tree)")
    if a.from_ocv:
        rows = CAP.load_rows(a.plan_json, a.corner, a.scale)
        if a.sta_proof:
            # count_align_plan.py --sta-proof (DIE-HEAD-5 one interval model) in the in-process plan (MESO-START-2)
            if not a.sta_plan:
                ap.error("--sta-proof needs --sta-plan")
            CAP.sta_rows_hull(rows, a)     # FLOW-ONEMODEL-1: the gate's per-port interval + measured fall
        if a.start_skew_clean and not any(a.start_skew):
            ap.error("--start-skew-clean needs --start-skew LO,HI")
        sedges, sroot, sinfo = CAP.start_tree_from_args(a, rows, ap.error)
        skw = dict(start_edges=sedges, start_root=sroot) if sedges is not None else {}
        s, out, regs = CAP.plan(rows, a.period, a.aperture, a.wander_frac, a.sync_aperture, a.pad,
                                CAP.parse_edge_pad(a.edge_pad), a.start_skew, a.start_skew_clean,
                                tree_parent=CAP.parse_edge_pad(a.tree_parent, str) or None, **skw)
        if sinfo:
            s["start_tree"].update(sinfo)
        if any(a.start_skew):
            s["start_skew_ps"] = list(a.start_skew)
        s.update(period_ps=a.period, aperture_ps=a.aperture, sync_aperture_ps=a.sync_aperture, pad=a.pad, scale=a.scale,
                 wander_frac=a.wander_frac, source=a.plan_json)
        plan = plan_doc(s, out, regs)
        if sedges is not None:
            plan["start_edges"] = [{k: v for k, v in e.items() if not k.startswith("_")} for e in sedges]
    else:
        plan = json.load(open(a.plan_json))
    table = json.load(open(a.table)) if a.table else None
    mode = ("table" if table else "region") if a.parts == "auto" else a.parts
    if mode == "ocv" and not a.from_ocv:
        raise SystemExit("--parts ocv needs --from-ocv")
    parts = (table_parts(table) if mode == "table" else
             ocv_parts(rows) if mode == "ocv" else None)
    b = bind(plan, parts=parts)
    v = verify(b, a.samples)
    rep = report(b, v)
    if parts is not None:
        rep["relay"] = relay_summary(b)
    rep["plan_source"] = a.plan_json
    rep["margin_policy"] = mpol
    b["report"] = rep
    Path(a.out).write_text(json.dumps(b, indent=0) + "\n")
    if a.table:
        t = annotate_table(table, b, a.root_settle, strap_form=a.strap_form)
        Path(a.table_out).write_text(json.dumps(t, indent=1) + "\n")
        if a.straps_out:
            st = strap_ties(t["count_aligned"], json.load(open(a.plan_die)))
            Path(a.straps_out).write_text(json.dumps(st, indent=1) + "\n")
            rep["straps"] = st["summary"]
    print(json.dumps(rep, indent=1))
    ok = not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
