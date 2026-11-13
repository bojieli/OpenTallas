#!/usr/bin/env python3
"""R-REACH-1 die-level relays (RULEBOOK-1113): registered relays on the die START provider and the landing monitor edges.

Plan step (opt-in, guarded): nothing else in the plan changes.

  START provider (landing_network.start_tree.provider, emitted_start_stage_rows): every stage -> stage edge whose
    conservative row-envelope hop exceeds the 405-um gate (TRIGGER) gets k = max(1, ceil(hop / TRUNK) - 1) relay stages
    (TRUNK 340 um), each one START flop + one bounded-reset relay flop (kind 'relay', module ot_die_start_relay,
    clocked from the PARENT stage's die clock-tree node net, row segment beside the trunk leg).  The stage keeps its logical parent and records fed_by (last relay) + relay_cycles k; the
    sidecar count_aligned region of that stage takes PAD += k and the report lists it as count_align_edge_pad (the
    count_align_plan --edge-pad input), so the count-aligned bind prices the boot cycles (K re-derived modulo the ring
    count width absorbs them; START is count-aligned).  No data cycle changes.
  Monitor edges (cland_mon_{ready,fault[,clk]}__<pid>): every bundle with an edge over the 405-um gate gets k relay sites
    shared by the bundle.  Seam bundle (with cland_mon_clk): the status is re-registered on its own forwarded clock at
    each site (falling-edge capture, rising-edge relaunch) and the clock passes through (fwd_clock_relay).  Same-region
    bundle (no clock edge): one region-clock flop per status bit at each site (die_clock_relay).  Status is level-sensitive: + k cycles
    of status latency, no data cycle.

  Relay sites: beside a die clock-tree trunk leg between two provider stage clock nodes (straight legs; for a START
  relay also either L of its own parent -> child leg) -- the same die-level site model as the existing provider stages
  (physical_qualified stays False; QC types declare no die_islands_um).

  plan PLAN SIDECAR --out-plan OUT --out-sidecar OUT_SIDE --report REPORT.json [--skip-unplaced-monitor]
  exit 2 if any relay could not be placed within SITE_MAX of both neighbours (nothing written).
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402
import start_provider_plan as SP  # noqa: E402

SITE_MAX = 395.0     # planned relay site reach (each segment)
TRIGGER = 405.0      # an edge is relayed only when it fails the 405-um reach gate
TRUNK = 340.0
FLOP_W = 1.08
ROW = 0.27
CLK_HALF = 0.81
GAP = 0.54
MAX_LOADS = 48
# start_stage_emit relay instance (ot_die_start_relay): one START flop + its one-flop bounded-reset relay
START_RELAY_MODULE = "ot_die_start_relay"
START_RELAY_FLOPS = 2
# clock_landings monitor relays: fwd_clock_relay = per status bit a falling-edge capture + rising-edge relaunch on the
# bundle's forwarded clock (ot_die_mon_relay_fwd); die_clock_relay = one region-clock flop per bit (ot_die_mon_relay)


class RelayError(ValueError):
    pass


def centre(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def targets(a, b, k):
    """k points at i/(k+1) of the Manhattan L path a -> b (x leg first)."""
    L = abs(b[0] - a[0]) + abs(b[1] - a[1])
    out = []
    for i in range(1, k + 1):
        d = L * i / (k + 1)
        dx = abs(b[0] - a[0])
        if d <= dx:
            out.append((a[0] + math.copysign(d, b[0] - a[0]), a[1]))
        else:
            out.append((b[0], a[1] + math.copysign(d - dx, b[1] - a[1])))
    return out


def _along(a, b, d):
    """point at Manhattan distance d from a on the L path a -> b (x leg first)"""
    dx = abs(b[0] - a[0])
    if d <= dx:
        return (a[0] + math.copysign(d, b[0] - a[0]), a[1])
    return (b[0], a[1] + math.copysign(d - dx, b[1] - a[1]))


def overlaps(r, rects):
    return any(r[0] < q[2] - 1e-6 and q[0] < r[2] - 1e-6 and r[1] < q[3] - 1e-6 and q[1] < r[3] - 1e-6 for q in rects)


class Grid:
    """bucketed rectangles for overlap queries"""
    B = 50.0

    def __init__(self, rects=()):
        self.b = {}
        for r in rects:
            self.add(r)

    def keys(self, r):
        for i in range(int(r[0] // self.B), int(r[2] // self.B) + 1):
            for j in range(int(r[1] // self.B), int(r[3] // self.B) + 1):
                yield i, j

    def add(self, r):
        for k in self.keys(r):
            self.b.setdefault(k, []).append(r)

    def hit(self, r):
        return any(overlaps(r, self.b.get(k, ())) for k in self.keys(r))


def trunks(pv):
    """straight die clock-tree trunk legs between provider clock nodes (parent stage clock node -> child stage clock
    node, same x or same y): the die-level sites the provider already uses (its stages sit beside these nodes)"""
    by = {n["id"]: n for n in pv["nodes"]}
    out = set()
    for e in pv["edges"]:
        if "src_stage" in e and "dst_stage" in e and e.get("signal") != "reset":
            a, b = by[e["src_stage"]], by[e["dst_stage"]]
            if a.get("kind") == "relay" or b.get("kind") == "relay":
                continue
            p, q = tuple(a["clock_node_xy_um"]), tuple(b["clock_node_xy_um"])
            if (abs(p[0] - q[0]) < 1e-6 or abs(p[1] - q[1]) < 1e-6) and p != q:
                out.add((min(p, q), max(p, q), a["clock_node"], b["clock_node"]))
    return sorted(out)


def load_trunks(doc):
    """built clock (QC-REGION-1 opentallas.qc_trunk_nodes.v1): stages {provider id: built node}, and the straight legs of
    the BUILT tree as trunk segments (lo, hi, a, b); legs the kit detoured (detour_um) carry no relay.  meta[seg] = leg."""
    if doc.get("schema") != "opentallas.qc_trunk_nodes.v1":
        raise RelayError(f"trunks: schema {doc.get('schema')!r}")
    segs, meta = [], {}
    for lg in doc["legs"]:
        if lg.get("detour_um"):
            continue
        p, q = tuple(lg["a_xy_um"]), tuple(lg["b_xy_um"])
        if p == q or not (abs(p[0] - q[0]) < 1e-6 or abs(p[1] - q[1]) < 1e-6):
            continue
        sg = (min(p, q), max(p, q), lg["a"], lg["b"])
        segs.append(sg)
        meta[sg] = lg
    return doc["stages"], sorted(segs), meta


def rewrite_provider(pv, stages):
    """every emitted START stage takes its BUILT clock node (no fallback to the old die H-tree node)"""
    miss = [n["id"] for n in pv["nodes"] if n.get("kind") != "relay" and n["id"] not in stages]
    if miss:
        raise RelayError(f"trunks: {len(miss)} provider nodes have no built clock node: {miss[:5]}")
    moved = []
    for n in pv["nodes"]:
        if n.get("kind") == "relay":
            raise RelayError("trunks: rewrite on a relayed provider (apply on a clean provider)")
        b = stages[n["id"]]
        old = (n["clock_node"], list(n["clock_node_xy_um"]))
        n.update(clock_node=b["clock_node"], clock_node_xy_um=list(b["clock_node_xy_um"]), clock_net=b.get("clock_net"),
                 clock_region=b.get("region"), clock_region_kind=b.get("region_kind"))
        moved.append(abs(old[1][0] - n["clock_node_xy_um"][0]) + abs(old[1][1] - n["clock_node_xy_um"][1]))
    moved.sort()
    return dict(nodes=len(moved), node_move_um=dict(median=round(moved[len(moved) // 2], 1), max=round(moved[-1], 1)))


def project(tg, seg):
    (a, b) = seg[0], seg[1]
    if abs(a[0] - b[0]) < 1e-6:
        return (a[0], min(max(tg[1], a[1]), b[1]))
    return (min(max(tg[0], a[0]), b[0]), a[1])


def trunk_sites(tg, segs, n=300, shifts=20):
    """candidate trunk points near tg: projection on each leg (nearest legs first), then shifted along the leg"""
    cand = sorted(((abs(project(tg, sg)[0] - tg[0]) + abs(project(tg, sg)[1] - tg[1]), i) for i, sg in enumerate(segs)))[:n]
    for _d, i in cand:
        sg = segs[i]
        pt = project(tg, sg)
        vert = abs(sg[0][0] - sg[1][0]) < 1e-6
        for m in [0] + [s_ * k for k in range(1, shifts) for s_ in (1, -1)]:
            q = (pt[0], pt[1] + 2.0 * m) if vert else (pt[0] + 2.0 * m, pt[1])
            lo, hi = sg[0], sg[1]
            if (vert and lo[1] <= q[1] <= hi[1]) or (not vert and lo[0] <= q[0] <= hi[0]):
                yield q, sg


def flop_rect(cxy, side, j, n=1):
    x0 = cxy[0] + GAP if side > 0 else cxy[0] - GAP - FLOP_W * n
    y0 = cxy[1] - ROW / 2 + j * ROW
    return [round(x0, 4), round(y0, 4), round(x0 + FLOP_W * n, 4), round(y0 + ROW, 4)]


def free_rect(cxy, taken, ok, n=1):
    for side in (1, -1):
        for j in (0, 1, -1, 2, -2, 3, -3, 4, -4):
            r = flop_rect(cxy, side, j, n)
            if not taken.hit(r) and ok(r):
                return r
    return None


def start_relays(P, pv, side_regions, built=None, rejected=None):
    """insert relay nodes on long stage -> stage edges; returns rows.  built = (segs, meta) of the built clock: relays
    sit on BUILT legs of the source stage's own clock region only (a leg of another region is rejected and counted)."""
    nodes, edges = pv["nodes"], pv["edges"]
    by = {n["id"]: n for n in nodes}
    taken = Grid([tuple(n["rect_um"]) for n in nodes])
    segs = trunks(pv) if built is None else built[0]
    rows, new_edges = [], []
    for e in edges:
        if not ("src_stage" in e and "dst_stage" in e) or e.get("signal") == "reset":
            new_edges.append(e)
            continue
        h = SP.hop(e["src_rect_um"], e["dst_rect_um"])
        if h <= TRIGGER + 1e-6:
            new_edges.append(e)
            continue
        src, dst = by[e["src_stage"]], by[e["dst_stage"]]
        if dst.get("kind") == "relay" or "fed_by" in dst:
            raise RelayError(f"stage {dst['id']} already relayed (apply on a clean provider)")
        k = max(1, math.ceil(h / TRUNK) - 1)
        prev, chain = src, []
        ca, cb = tuple(src["clock_node_xy_um"]), tuple(dst["clock_node_xy_um"])
        Lc = abs(cb[0] - ca[0]) + abs(cb[1] - ca[1])
        for i in range(k):
            last = i == k - 1
            best = None

            def ok(r, prev=prev, last=last):
                return SP.hop(prev["rect_um"], r) <= SITE_MAX and (not last or SP.hop(r, dst["rect_um"]) <= SITE_MAX) and \
                    SP.hop(r, dst["rect_um"]) <= SITE_MAX * (k - i)
            # the tree leg src node -> dst node: straight, or either L of it (its wire runs one of them)
            own = [(ca, cb)] if (abs(ca[0] - cb[0]) < 1e-6 or abs(ca[1] - cb[1]) < 1e-6) else \
                [(ca, (cb[0], ca[1])), ((cb[0], ca[1]), cb), (ca, (ca[0], cb[1])), ((ca[0], cb[1]), cb)]
            own = [(min(p_, q_), max(p_, q_), src["clock_node"], dst["clock_node"]) for p_, q_ in own]
            tg = _along(ca, cb, (i + 1) / (k + 1) * Lc)
            if built is not None:       # the built tree: no implied src -> dst leg; legs of src's clock region only
                own = []
                cand = []
                for cxy, sg in trunk_sites(tg, segs):
                    if built[1][sg].get("region") != src.get("clock_region"):
                        if rejected is not None:
                            rejected.add((src["id"], dst["id"], built[1][sg].get("region")))
                        continue
                    cand.append((cxy, sg))
            else:
                cand = list(trunk_sites(tg, segs))
            for cxy, sg in list(trunk_sites(tg, own, 4, 60)) + cand:
                r = free_rect(cxy, taken, ok, n=START_RELAY_FLOPS)
                if r:
                    best = (src["clock_node"], (round(cxy[0], 4), round(cxy[1], 4)), r, sg)
                    break
            if best is None:
                raise RelayError(f"no relay site within {SITE_MAX} um for {src['id']} -> {dst['id']} (hop {h:.1f})")
            cn, cxy, r, sg = best
            taken.add(tuple(r))
            rid = f"{dst['id']}_rl{i + 1}"
            rn = dict(id=rid, region=f"{dst['region']}#rl{i + 1}", kind="relay", relay_for=dst["region"], rect_um=r,
                      clock_node=cn, clock_node_xy_um=list(cxy), clock_port=f"t_st_{rid}__clk",
                      clock_tap=f"trunk {sg[2]} -> {sg[3]}",
                      **({} if built is None else dict(clock_net=src.get("clock_net"), clock_region=src.get("clock_region"),
                                                       site_net=built[1][sg].get("net"))),
                      module=START_RELAY_MODULE, flops=START_RELAY_FLOPS, parent=prev["region"], root=False)
            nodes.append(rn)
            by[rid] = rn
            new_edges.append(dict(src_stage=prev["id"], dst_stage=rid, src_rect_um=prev["rect_um"], dst_rect_um=r,
                                  max_hop_um=405, source_registered=True, capture_registered=True))
            chain.append(rn)
            prev = rn
        new_edges.append(dict(e, src_stage=prev["id"], src_rect_um=prev["rect_um"]))
        dst["fed_by"] = prev["region"]
        dst["relay_cycles"] = k
        reg = side_regions.get(dst["region"])
        if reg is None:
            raise RelayError(f"sidecar count_aligned has no region {dst['region']}")
        reg["pad"] = int(reg.get("pad", 0)) + k
        rows.append(dict(src=src["id"], dst=dst["id"], region=dst["region"], hop_um=round(h, 1), relays=k,
                         hops_um=[round(SP.hop(a, b), 1) for a, b in zip([src["rect_um"]] + [c["rect_um"] for c in chain],
                                                                        [c["rect_um"] for c in chain] + [dst["rect_um"]])],
                         clock_access_um=[round(SP.hop(list(c["clock_node_xy_um"]) * 2, c["rect_um"]), 2) for c in chain]))
    pv["edges"] = new_edges
    return rows


def pin_die(P, part, bus):
    q = [q for q in P.ptype(part)["clock"]["landing_contract"]["pins"] if q["name"] == bus]
    return tuple(P.to_die(part, q[0]["xy_um"]))


def mon_relays(P, ln, segs, taken, unplaced=None):
    groups = {}
    for e in ln["edges"]:
        if e["id"].startswith("cland_mon_"):
            groups.setdefault(e["id"].split("__", 1)[1], []).append(e)
    rows = []
    for g, es in sorted(groups.items()):
        pts = {e["id"]: (pin_die(P, e["src"]["part"], e["src"]["bus"]), pin_die(P, e["dst"]["part"], e["dst"]["bus"])) for e in es}

        def worst(e):
            ch = [pts[e["id"]][0]] + [tuple(r["xy_um"]) for r in e.get("relays", [])] + [pts[e["id"]][1]]
            return max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(ch, ch[1:]))
        if max(worst(e) for e in es) <= TRIGGER + 1e-6:
            continue                                       # within reach (directly or through its relays): no-op
        h = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in pts.values())
        clk = [e for e in es if e["kind"] == "clock"]
        if len(clk) > 1 or any((e["src"]["part"], e["dst"]["part"]) != (es[0]["src"]["part"], es[0]["dst"]["part"]) for e in es):
            raise RelayError(f"monitor bundle {g}: not (at most one forwarded clock +) status edges on the same parts")
        form = "fwd_clock_relay" if clk else "die_clock_relay"   # seam: status on the source's forwarded clock;
        lead = (clk or es)[0]                                     # same region: status on the die clock
        if any("relays" in e for e in es):
            raise RelayError(f"monitor bundle {g}: already relayed")
        k = max(1, math.ceil(h / TRUNK) - 1)
        a, b = pts[lead["id"]]
        sites, nodes = [], []
        for i, tg in enumerate(targets(a, b, k)):
            last = i == k - 1

            def ok(r, last=last):
                for s_, d_ in pts.values():
                    p0 = sites[-1] if sites else s_
                    if SP.hop(list(p0) * 2, r) > SITE_MAX or (last and SP.hop(r, list(d_) * 2) > SITE_MAX):
                        return False
                    if not last and SP.hop(r, list(d_) * 2) > SITE_MAX * (k - i):
                        return False
                return True
            best = None
            for cxy, sg in trunk_sites(tg, segs):
                bits = len([e for e in es if e["kind"] == "ctl"])
                r = free_rect(cxy, taken, ok, n=bits * (2 if clk else 1))
                if r:
                    best = (r, cxy, sg)
                    break
            if best is None:
                msg = f"monitor bundle {g}: no die-level relay site within {SITE_MAX} um (hop {h:.1f})"
                if unplaced is None:
                    raise RelayError(msg)
                unplaced.append(dict(bundle=g, src=lead["src"]["part"], dst=lead["dst"]["part"], hop_um=round(h, 1),
                                     edges=[e["id"] for e in es], why=msg))
                sites = None
                break
            taken.add(tuple(best[0]))
            sites.append(tuple(round(v, 4) for v in centre(best[0])))
            nodes.append((round(best[1][0], 4), round(best[1][1], 4), best[2][3]))
        if sites is None:
            continue
        for e in es:
            e["relays"] = [dict(id=f"rl_{g}_{i + 1}", kind=form, xy_um=list(s),
                                **({} if clk else dict(clock_node=nd[2], clock_node_xy_um=[nd[0], nd[1]])))
                           for i, (s, nd) in enumerate(zip(sites, nodes))]
            e["relay_group"] = f"cland_mon__{g}"
        seglen = []
        for s_, d_ in pts.values():
            chain = [s_] + sites + [d_]
            seglen.append(max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(chain, chain[1:])))
        rows.append(dict(bundle=g, form=form, src=lead["src"]["part"], dst=lead["dst"]["part"], edges=len(es), hop_um=round(h, 1),
                         relays=k, sites=sites, max_segment_um=round(max(seglen), 1)))
    return rows


def depth_stats(pv):
    by = {n["region"]: n for n in pv["nodes"]}
    memo = {}

    def d(r):
        if r in memo:
            return memo[r]
        n = by[r]
        f = SP.feed_region(n)
        memo[r] = (1 if f not in by else d(f)[0] + 1, (1 if n.get("kind") == "relay" else 0) + (0 if f not in by else d(f)[1]))
        return memo[r]
    ds = {r: d(r) for r in by}
    leaves = {e["src_stage"] for e in pv["edges"] if e.get("pin") == "cland_tstart_in"}
    ids = {n["id"]: n["region"] for n in pv["nodes"]}
    lv = [ds[ids[i]] for i in leaves]
    kids = {}
    for e in pv["edges"]:
        if "src_stage" in e and e.get("signal") != "reset":
            kids[e["src_stage"]] = kids.get(e["src_stage"], 0) + 1
    return dict(max_depth=max(x[0] for x in lv), max_relays_on_path=max(x[1] for x in lv),
                max_loads=max(kids.values()) if kids else 0)


def plan(raw, side, skip_unplaced=False, trunks_doc=None):
    raw, side = copy.deepcopy(raw), copy.deepcopy(side)
    P = S.Plan(raw)
    ln = raw["clock"]["landing_network"]
    pv = ln["start_tree"]["provider"]
    before = depth_stats(pv)
    regions = side["count_aligned"]["regions"]
    built, rewrite, rejected = None, None, set()
    if trunks_doc is not None and not any(n.get("kind") == "relay" for n in pv["nodes"]):
        stages, bsegs, meta = load_trunks(trunks_doc)
        rewrite = rewrite_provider(pv, stages)
        rewrite.update(clock_build=trunks_doc.get("clock_build"), plan_sha256=trunks_doc.get("plan_sha256"),
                       legs=len(bsegs), legs_detoured=sum(1 for lg in trunks_doc["legs"] if lg.get("detour_um")))
        built = (bsegs, meta)
        ln["start_tree"]["built_clock"] = dict(schema=trunks_doc["schema"], clock_build=trunks_doc.get("clock_build"),
                                               plan_sha256=trunks_doc.get("plan_sha256"))
    elif trunks_doc is not None:
        _s, bsegs, meta = load_trunks(trunks_doc)
        built = (bsegs, meta)
    segs = trunks(pv) if built is None else built[0]
    srows = start_relays(P, pv, regions, built, rejected)
    taken = Grid([tuple(n["rect_um"]) for n in pv["nodes"]])
    unplaced = [] if skip_unplaced else None
    mrows = mon_relays(P, ln, segs, taken, unplaced)
    after = depth_stats(pv)
    if after["max_loads"] > MAX_LOADS:
        raise RelayError(f"provider stage drives {after['max_loads']} loads > {MAX_LOADS}")
    chk = SP.check(S.Plan(raw), pv)
    rep = dict(schema="opentallas.reach_relay_plan.v1", site_max_um=SITE_MAX, trigger_um=TRIGGER, trunk_um=TRUNK,
               start=dict(edges=len(srows), relays=sum(r["relays"] for r in srows), before=before, after=after,
                          boot_cycles_added_max_path=after["max_relays_on_path"],
                          # count_align_plan --edge-pad input (MESO-RECONCILE-1: per start-tree edge PAD, keyed by child
                          # region): the bind re-derives n_nominal and K from it (K mod ring count width: data latency kept)
                          count_align_edge_pad={r["region"]: int(regions[r["region"]]["pad"]) for r in srows},
                          provider_check=dict(errors=chk["errors"][:20], n_errors=len(chk["errors"]),
                                              max_hop_um=chk["max_hop_um"], max_clock_access_um=chk["max_clock_access_um"]),
                          rows=srows),
               monitor=dict(bundles=len(mrows), relays=sum(r["relays"] for r in mrows),
                            edges=sum(r["edges"] for r in mrows), status_cycles_added_max=max([r["relays"] for r in mrows] or [0]),
                            unplaced=unplaced or [], rows=mrows),
               data_cycles_added=0)
    if trunks_doc is not None:
        rep["built_clock"] = dict(rewrite=rewrite, rejected_region_sites=len(rejected),
                                  rejected_edges=len({(a, b) for a, b, _r in rejected}),
                                  rejected_examples=sorted(rejected)[:10],
                                  max_relay_segment_um=max([max(r["hops_um"]) for r in srows] or [0]))
    return raw, side, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("plan")
    p.add_argument("sidecar")
    p.add_argument("--out-plan", required=True)
    p.add_argument("--out-sidecar", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--skip-unplaced-monitor", action="store_true",
                   help="leave a monitor bundle with no relay site unchanged (listed in report.monitor.unplaced; its "
                        "reach rows stay in the gates) instead of failing the step")
    p.add_argument("--trunks", help="built clock trunk_nodes.json (opentallas.qc_trunk_nodes.v1): rewrite the provider "
                   "clock nodes from it and seat relays on its legs (same clock region as the source stage)")
    a = ap.parse_args(argv)
    try:
        raw, side, rep = plan(json.loads(Path(a.plan).read_text()), json.loads(Path(a.sidecar).read_text()),
                              a.skip_unplaced_monitor,
                              json.loads(Path(a.trunks).read_text()) if a.trunks else None)
    except RelayError as ex:
        print(f"reach_relay_plan: NOT PLACED: {ex}", file=sys.stderr)
        return 2
    Path(a.report).write_text(json.dumps(rep, indent=1))
    Path(a.out_plan).write_text(json.dumps(raw, indent=1))
    Path(a.out_sidecar).write_text(json.dumps(side, indent=1))
    s = rep["start"]
    print(f"reach_relay_plan: START {s['edges']} edges +{s['relays']} relays (depth {s['before']['max_depth']} -> "
          f"{s['after']['max_depth']}, max +{s['boot_cycles_added_max_path']} boot cycles on a path, provider errors "
          f"{s['provider_check']['n_errors']}); monitor {rep['monitor']['bundles']} bundles +{rep['monitor']['relays']} relays, "
          f"{len(rep['monitor']['unplaced'])} unplaced {[u['bundle'] for u in rep['monitor']['unplaced']]}")
    return 1 if s["provider_check"]["n_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
