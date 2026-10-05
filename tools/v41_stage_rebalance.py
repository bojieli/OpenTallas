#!/usr/bin/env python3
"""V4.1 ROM array: stage / layer rebalancing levers for the index-scan imbalance.  Model work only.

    python3 tools/v41_stage_rebalance.py [--out results/arch/v41_stage_rebalance.json]

The finding (design-point re-derivation, 2026-09-28): four V4.1 layers scan their whole index-key cache every token
(configs: modes[L].scans_index with index_scan_entries_cap 0) -- layers 2, 8 and 14 (compress ratio 2: ctx / 2 keys)
and layer 20 (ratio 1: ctx keys, plus the candidate-block branch the reindex layers 24/28/32/36 use).  The reindex
layers are capped at 16,384 keys, every other layer reuses a source layer's selection.  The placement
(results/arch/v41_die_placement.json, packed by ROM bytes) puts each scanning layer's attention -- and therefore its
key cache in the group's HBM, its scan and its top-512 select -- on the stage where the layer starts: layer 2 on S1,
8 on S5, 14 on S9 and 20 on S14.  At 1M the scan is HBM-bandwidth bound (68-B FP4 keys, 262,144 keys per die for
layer 20) and its select streams every score, so S14 is busy 3.4x the stage mean at batch 1, its die is the hottest
(6.9x the mean die's energy per token) and at the 28-user fill and at saturation S14's occupancy bounds the pipeline.

The levers (each a scenario of this record).  The adoption rule (user decisions 2026-09-28): the V4.1 machines are
liquid-cooled (474.6 W per die of a two-die package; air, 374.6 W, is a sensitivity) and the hottest die must fit the
liquid limit at EVERY operating point -- batch 1, the 28-user fill and the saturated batch, each with and without MTP,
over a context sweep from 200K to 1M -- by rebalancing, not by assuming more cooling; the batch-1 autoregressive rate
must not drop at any context; no hardware the rack does not have; a throughput / energy gain.  The batch-1 MTP rate is
reported against the design point before rebalancing:

(i)   RE-MAP LAYERS TO STAGES.  The stage count and the ring are fixed by the rack; stage membership is not.  But every
      layer die's ROM is packed to within 8.6 MB of its capacity after the Engram spill (die_table), so a stage cannot
      take another stage's layer bytes: whole layers cannot move.  What CAN move without ROM is the work that does not
      read ROM -- a scanning layer's key cache lives in HBM, and its scan and select read only that cache and the
      layer's index query.  The pure re-map (the whole scan on another stage's dies) is scenario remap_scan_S13: the
      scan moves to the lightest neighbour, but the query and the candidates now cross the fabric on the critical
      path with no parallel gain.
(ii)  SPLIT A SCAN-HEAVY LAYER'S INDEX SCAN OVER MORE DIES.  A layer's key cache is split by POSITION RANGE: the home
      group keeps positions [0, lo) and every helper group keeps [lo_i, hi_i).  Each helper group (the 4 dies of
      another stage; every layer die has the same indexer engine, select unit and 4 HBM3E stacks) receives the index
      query (32 heads x 128 FP4 + UE8M0 scales = 2,176 B per die), scans its range from its own stacks, runs its local
      top-512 (and, for layer 20, the candidate-block top-k) and returns its (score, position) lists (4 KB + 512 B per
      die); the home group's merge takes 4 more lists per helper.  Links: the stage ring runs one way (a package's
      stage lanes go out to the next module and in from the previous), so every helper exchange uses one ring hop in
      the ring's direction and one switched traversal (the 4 switch lanes every layer package already carries to the
      rack's 51.2T switch): an UPSTREAM helper (stage s - 1) gets the query through the switch and returns on the ring
      (s - 1 -> s), a DOWNSTREAM helper (s + 1) gets the query on the ring and returns through the switch.  The ring
      hop is priced as every stage hop is (the stage lanes, the bench-measured stage-hop tail of the collective-lever
      campaign, the SerDes-edge on-die wire); the switched traversal at the rack's switched one-way latency (full-KP4
      port hop + 250 ns switch + port hop + cable, tools/v41_rack_design.switched_one_way_s), the bytes on the die's
      2 of its package's 4 switch lanes, and the same measured stage-hop residual as a surrogate tail (conservative:
      the switch path has no bench).  A helper ENGAGES only for a user whose context has reached its engage
      position: below it the home group scans the whole cache from its own copy of the helper's range (keys appended
      in [lo, engage) are written to both), so a helper whose share is too small to repay the round trip never runs;
      the batch-1 rate is checked over a context sweep that brackets every engage position.  Capacity: at 1M the home
      group holds fewer keys than before (the capacity-binding die), so the users held could rise; this record keeps
      the capacity bound as it was (conservative).
      The ratio-2 scans (layers 2, 8, 14) are half as long as layer 20's at the same context: no range or engage
      point lets a switched helper repay its round trip at batch 1 (scenario split_all_scans).  With MTP, though, their
      home dies (S1, S5, S9) exceed the liquid limit -- at batch 1 past ~915K, in the saturated batch past ~750K -- so
      the adopted plan gives each an upstream helper (S0, S4, S8) that keeps a copy of its keys from 700K and scans it
      ONLY in MTP verify passes (the home keeps its full cache, so the choice is per pass): in a saturated batch from
      700K, at batch 1 and the fill from 900K.  That is the one place the liquid rule costs rate: the batch-1 MTP rate
      between 900K and ~1M (verdict mtp_batch1_worst_ratio), less than the liquid cap would take.
      The drafter's power on the head dies is priced from its own ops (tools/power_scenarios.v41_hottest_die): the
      former proxy (7.5% of every layer die's verify energy) charged it the target's 1M index scans, which its
      window-only attention does not run.
(iii) DUTY-CYCLE / THROTTLE (last resort): the thermal cap already in the power model (power_scenarios cooling_classes
      capped_rate): the aggregate the hottest die allows under air or liquid.  It only slows the machine.
(iv)  USE THE STACKS / ENGINES DIFFERENTLY PER STAGE.  More stacks on S14's dies is ruled out (4 per die is the
      shipping-interposer cap, arch_budget_v41 HBM_STACKS_PER_DIE_MAX); the scan is HBM-bound, so a wider indexer does
      nothing.  Lever (ii) IS the per-stage use of the stacks: the helper stages' stacks are otherwise idle during the
      scan.  The one compute variant is a wider select unit on every die (sel_lanes 64 -> 128): it shortens every
      top-512, charged its area on all 116 dies.

Every scenario is priced on the design-point model (tools/arch_lanes_v41.design_point: the adopted ladder, lane split,
on-die wire and bench-measured collective tails with the adopted levers): batch-1 per-user rates with and without MTP,
the 28-user fill and the saturated points (link-capped as the lanes record), stage occupancy, the hottest die's power
with its air / liquid verdict per operating point (tools/power_scenarios.v41_points, scenario B inputs), energy per
token, rack input power (tools/v41_rack_design.power's wall chain) and area.  A design-point model result, not
measured chip throughput.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

SCHEMA = "opentallas.v41-stage-rebalance.v1"
OUT = ROOT / "results/arch/v41_stage_rebalance.json"
G = 4                                               # tensor group (dies per stage)
FILL = 28                                           # up to the fill every user rides the batch-1 path (one per stage)
IDX_Q_BYTES = 32 * 128 // 2 + 32 * 128 // 32       # index query per die: FP4 + one UE8M0 scale per 32
SCAN_OPS = ("attn.idx.score", "attn.idx.relu_w_headsum", "attn.idx.topk", "attn.cand.blockmax", "attn.cand.topk")
SWEEP = (131072, 200000, 262144, 400000, 524288, 600000, 625000, 650000, 660000, 700000, 786432, 800000, 850000,
         880000, 900000, 910000, 950000, 1000000, 1048576)
POWER_SWEEP = (200000, 400000, 524288, 599000, 600000, 650000, 700000, 800000, 880000, 899000, 900000, 950000,
               1000000, 1048576)


def H(stage, lo, hi=None, side="up", share=1.0, engage=None, mtp_only=False, engage_b1=None):
    """A helper group: the 4 dies of `stage` hold `share` of the key positions [lo, hi) of the layer (share < 1:
    interleaved blocks, the home group keeps the rest); side 'up' (stage s - 1: query through the switch, return on
    the ring), 'upN' (stage s - N: the return relayed over N ring hops), 'down' (stage s + 1: query on the ring,
    return through the switch) or 'local' (stage s - 1 computing the layer's index query itself from its own copy of
    the query path's weights -- it holds the whole preceding layer -- and returning on the ring).  engage: the
    helper scans only for a user whose context has reached it; below it the home group scans the whole cache from its
    own copy of [lo, engage) (every key the home group appends is written to both until then: at most
    (engage - lo) x 68 B more per user in the home group's HBM), so a helper whose share would be too small to repay
    its round trip never runs.  mtp_only: the helper scans only in MTP verify passes (a key-cache split the home
    group keeps a full copy of, so the scheduler can choose it per pass); engage_b1: a later engage position for a
    pass at or below the pipeline fill (each user on the batch-1 path) than for a saturated batch (a batch's
    aggregate gains where a single user's rate would not)."""
    return dict(stage=stage, lo=lo, hi=hi, side=side, share=share, engage=engage or lo, mtp_only=mtp_only,
                engage_b1=engage_b1)


# the scenarios: {layer: [helpers]} (positions are decode positions; a ratio-2 layer's key k covers positions 2k, 2k+1)
PLANS = {
    "baseline": {},
    "remap_scan_S13": {20: [H(13, 0, None, "up")]},
    "split_L20_S13": {20: [H(13, 600000, None, "up", 1.0, 650000)]},
    "split_L20_S13_S12": {20: [H(13, 400000, 800000, "up", 1.0, 650000), H(12, 800000, None, "up2", 1.0, 900000)]},
    "split_L20_S13_S12_r2_mtp": {
        20: [H(13, 400000, 800000, "up", 1.0, 400000, engage_b1=600000),
             H(12, 800000, None, "up2", 1.0, 800000, engage_b1=900000)],
        **{L: [H(s, 700000, None, "up", 1.0, 700000, mtp_only=True, engage_b1=900000)] for L, s in ((2, 0), (8, 4), (14, 8))}},
    "split_L20_S13_S15": {20: [H(13, 400000, 800000, "up", 1.0, 650000), H(15, 800000, None, "down", 1.0, 900000)]},
    "split_L20_S13_S12_no_engage": {20: [H(13, 400000, 800000, "up"), H(12, 800000, None, "up2")]},
    "split_L20_S13_local": {20: [H(13, 65536, None, "local", 0.5)]},
    "split_all_scans": {20: [H(13, 400000, 800000, "up", 1.0, 650000), H(12, 800000, None, "up2", 1.0, 900000)],
                        14: [H(8, 700000, None, "up", 1.0, 800000)], 8: [H(4, 700000, None, "up", 1.0, 800000)],
                        2: [H(0, 700000, None, "up", 1.0, 800000)]},
}
ADOPTED = "split_L20_S13_S12_r2_mtp"                        # the adopted plan (arch_lanes_v41.design_point runs it)
_ACTIVE = []


def active_plan():
    """The plan the design point runs (the innermost `using` plan, else the adopted one, else none)."""
    if _ACTIVE:
        return _ACTIVE[-1]
    return PLANS[ADOPTED] if ADOPTED else {}


@contextlib.contextmanager
def using(plan):
    _ACTIVE.append(plan)
    try:
        yield
    finally:
        _ACTIVE.pop()


def engaged(h, positions, mtp=False, batch=1):
    """Whether helper h scans in a pass at `positions` context: past its engage position (engage_b1 for a batch-1
    pass, when given), and in an MTP verify pass if it is mtp_only."""
    if h.get("mtp_only") and not mtp:
        return False
    e = h.get("engage_b1") if (batch <= FILL and h.get("engage_b1")) else h.get("engage", h["lo"])
    return positions >= e


def fractions(helpers, positions, mtp=False, batch=1):
    """(home share, [helper shares]) of a layer's keys at `positions` decode positions (position ranges) in a pass of
    the given kind (MTP verify or not; batch 1 or a batch)."""
    fr = [h.get("share", 1.0) * max(0, min(positions, h["hi"] or positions) - h["lo"]) / positions
          if engaged(h, positions, mtp, batch) else 0.0 for h in helpers]
    return 1.0 - sum(fr), fr


def switched_one_way_s():
    import v41_rack_design as RK
    return RK.switched_one_way_s()


def _sel(A, name, nd, sp, c, r, per_die, clock):
    """(issue per unit microbatch, tail) seconds of a select node at per_die keys (the budget's select pricing)."""
    iss, tail, _r, _w = A._select_price(name, nd, sp, c, per_die * G * r, 1.0, clock)
    return iss, tail


def local_front(g, P, s, c, L):
    """Clones (on stage s) of the layer's attention front that the index scan needs -- the hyper-connection
    collapse, norm and quantisation, the fused a_proj (only its wq_a and indexer weights_proj rows: its issue scaled
    to their bytes), its all-gather, q_norm and the indexer's rows of wq_b (issue scaled to IH x IHD of its outputs)
    -- with the same inputs as the home group's (the previous layer's output, which the helper holds)."""
    D_, H_, HD, QR, IH, IHD = (c["hidden_size"], c["num_attention_heads"], c["head_dim"], c["q_lora_rank"],
                               c["index_heads"], c["index_head_dim"])
    need, stack = set(), [f"{P}.idx.q", f"{P}.a_allgather"]
    while stack:
        n = stack.pop()
        if n in need or not n.startswith(P + "."):
            continue
        need.add(n)
        stack += g.nodes[n]["deps"]
    ratio = c["compress_ratios"][L]
    is_src = L in c["kv_source_layer_ids"]
    a_bytes = ((QR + HD) * D_ + IH * D_ * 2 + (2 * HD * D_ * 4 if (is_src and ratio == 2) else HD * D_ * 2 if is_src
                                              else 0))
    scale = {f"{P}.a_proj": (QR * D_ + IH * D_ * 2) / a_bytes, f"{P}.wq_b": IH * IHD / (H_ * HD + IH * IHD)}
    ren = {n: n.replace(P + ".", f"{P}.h{s}.", 1) for n in need}
    out = []
    for n, nd in g.nodes.items():
        if n not in need:
            continue
        x = copy.deepcopy(nd)
        x.update(name=ren[n], deps=[ren.get(d, d) for d in nd["deps"]], exec_stage=s,
                 issue=nd["issue"] * scale.get(n, 1.0))
        out.append(x)
    return out


def front_rom_bytes(c, L):
    """ROM bytes per die the 'local' helper stores for layer L's front (local_front's weights): the HC mixes
    (replicated), wq_a + indexer weights_proj (tensor-split), the indexer's wq_b rows (replicated)."""
    D_, HC, QR, IH, IHD = c["hidden_size"], c["hc_mult"], c["q_lora_rank"], c["index_heads"], c["index_head_dim"]
    hc = 6 * HC * HC * D_ * 4
    return dict(hc_mixes=hc, wq_a_and_weights_proj=(QR * D_ + IH * D_ * 2) / G, indexer_wq_b=IH * IHD * QR,
                total=hc + (QR * D_ + IH * D_ * 2) / G + IH * IHD * QR)


def split_mutation(plan, hop_term=None):
    """DAG mutation (tools/arch_utilization_v41.solve muts): run AFTER the design point's mutations (its on-die wire
    included: the new nodes copy the wire of the nodes they clone) and BEFORE the lane pricing and the measured
    collective exposure (arch_lanes_v41.m_lanes prices the ring hops' bytes, collective_exposure the ring hops'
    measured tail).  hop_term: the design point's measured stage-hop exposure term (window + residual), charged on the
    switched traversals as a surrogate tail (the attribute hop_term, read at call time).  Helper nodes carry
    exec_stage (arch_budget_v41.stage_occupancy)."""
    import arch_budget_v41 as A

    def m_split(g, sp):
        if not plan:
            return
        E = A._env()
        c, clock = E["c"], E["clock"]
        cyc = 1.0 / clock
        TOPK, CK = c["index_topk"], c["candidate_topk_blocks"]
        mb = getattr(g, "mb", 1.0) * getattr(g, "positions", 1)
        hops = [nd for nd in g.nodes.values() if nd["kind"] == "hop" and nd.get("hop_kind") in ("stage", "substage")]
        ring_t = max(hops, key=lambda nd: nd["depth"])            # a board stage hop (the ring link)
        sw_lat = switched_one_way_s()
        import arch_lanes_v41 as AL
        sw_bps = AL.SWITCH / 2 * AL.LANE_NET_BPS                   # a die's half of its package's 4 switch lanes
        ucie_hop = A.links_for(A.BASELINE)["rom_package_ucie"]["hop"]
        inserts = {}

        def hop(name, dep, L, payload, route, producer_issue):
            """route 'ring': one stage hop in the ring's direction (lanes, measured tail and wire as every stage hop);
            'switch_q': the query through the switch, one copy per package on its 4 switch lanes, then UCIe to the
            package's second die; 'switch': a per-die list through the switch on the die's 2 of the 4 lanes."""
            nd = dict(ring_t)
            for k in ("_exposed", "_stream_issue_s"):
                nd.pop(k, None)
            nd.update(name=name, deps=[dep], layer=L, payload=payload, desc=f"rebalance: {route} ({payload} B/die)")
            if route == "ring":
                nd["hop_kind"] = "stage"                          # the lanes and the measured tail price it
                nd["issue"] = payload * mb / (2 * 14 * AL.LANE_NET_BPS)
                return nd
            nd["hop_kind"] = "switch"
            if route == "switch_q":
                by = payload * mb / (AL.SWITCH * AL.LANE_NET_BPS) + payload * mb / AL.UCIE_BPS
                nd["depth"] = sw_lat + ucie_hop
            else:
                by = payload * mb / sw_bps
                nd["depth"] = sw_lat
            ht = m_split.hop_term
            if ht:
                win = producer_issue if ht["window"] == "producer" else ht["window_s"]
                by = max(0.0, by - win) + ht["residual_s"]
            nd.update(issue=by, stream=False, ctrl=0.0, _exposed="switch (stage-hop residual as surrogate)")
            return nd

        for L, helpers in plan.items():
            P = f"L{L}.attn"
            sc = g.nodes.get(f"{P}.idx.score")
            if sc is None:
                continue
            r = c["compress_ratios"][L]
            per_die = int(sc["desc"].split()[2])
            f0, fr = fractions(helpers, per_die * G * r, getattr(g, "positions", 1) > 1, getattr(g, "batch", 1))
            live = [(h, f) for h, f in zip(helpers, fr) if f > 0]
            if not live:
                continue
            names = [f"{P}.idx.topk_local"] + ([f"{P}.cand.topk_local"] if f"{P}.cand.topk_local" in g.nodes else [])
            base = {n: copy.deepcopy(g.nodes[n]) for n in [f"{P}.idx.score"] + names}
            full = {n: _sel(A, n, base[n], sp, c, r, per_die, clock) for n in names}

            def scaled(n, f):
                nd = copy.deepcopy(base[n])
                if n.endswith("idx.score"):
                    nd["issue"] = base[n]["issue"] * f             # bytes and MACs both linear in the keys
                    return nd
                i1, t1 = _sel(A, n, base[n], sp, c, r, max(1, math.ceil(per_die * f)), clock)
                i0, t0 = full[n]
                nd["issue"] = base[n]["issue"] * (i1 / i0 if i0 else f)
                nd["depth"] = max(0.0, base[n]["depth"] + t1 - t0)
                return nd

            for n in [f"{P}.idx.score"] + names:                   # the home group keeps [0, lo)
                g.nodes[n].update({k: v for k, v in scaled(n, f0).items() if k in ("issue", "depth")})
            new = []
            for h, f in live:
                s = h["stage"]
                up = h["side"].startswith("up") or h["side"] == "local"
                if h["side"] == "local":
                    new += local_front(g, P, s, c, L)
                    hs = scaled(f"{P}.idx.score", f)
                    hs.update(name=f"{P}.idx.h{s}.score", exec_stage=s,
                              deps=[f"{P}.h{s}.idx.q", f"{P}.h{s}.a_allgather"])
                    q = None
                else:
                    q = hop(f"{P}.idx.h{s}.query", f"{P}.idx.q", L, IDX_Q_BYTES, "switch_q" if up else "ring",
                            g.nodes[f"{P}.idx.q"]["issue"])
                    hs = scaled(f"{P}.idx.score", f)
                    hs.update(name=f"{P}.idx.h{s}.score", deps=[q["name"]], exec_stage=s)
                out = []
                for n in names:
                    x = scaled(n, f)
                    x.update(name=n.replace(".topk_local", f".h{s}.topk_local"), deps=[hs["name"]], exec_stage=s)
                    out.append(x)
                pay = (TOPK + (CK if len(names) > 1 else 0)) * 8
                rets = []
                n_ring = (int(h["side"][2:] or 1) if h["side"].startswith("up") else 1) if up else 0   # 'up2': relayed
                for i in range(max(1, n_ring)):
                    x = hop(f"{P}.idx.h{s}.return" + (f"{i}" if n_ring > 1 else ""),
                            rets[-1]["name"] if rets else out[0]["name"], L, pay, "ring" if up else "switch",
                            rets[-1]["issue"] if rets else max(x["issue"] for x in out))
                    if not rets:
                        x["deps"] = [y["name"] for y in out]
                    rets.append(x)
                new += ([q] if q else []) + [hs] + out + rets
            inserts[f"{P}.idx.topk_merge"] = new
            nh = len(live)
            for mg, fin, k in ((f"{P}.idx.topk_merge", f"{P}.idx.topk_final", TOPK),
                               (f"{P}.cand.merge", f"{P}.cand.final", CK)):
                if mg in g.nodes:
                    g.nodes[mg]["deps"] = g.nodes[mg]["deps"] + [
                        x["name"] for i, x in enumerate(new) if ".return" in x["name"]
                        and (i + 1 == len(new) or ".return" not in new[i + 1]["name"])]
                    g.nodes[mg]["payload"] = g.nodes[mg]["payload"] * (1 + nh)
                if fin in g.nodes:                                 # the final merge ingests 4 more lists per helper
                    g.nodes[fin]["depth"] += math.ceil(G * k * nh / max(1, sp.sel_lanes)) * cyc
        if inserts:
            nodes = {}
            for n, nd in g.nodes.items():
                for x in inserts.get(n, []):
                    nodes[x["name"]] = x
                nodes[n] = nd
            g.nodes = nodes
    m_split.__name__ = "stage_rebalance_split"
    m_split.hop_term = hop_term                      # late-bound: arch_lanes_v41.build sets it once its terms exist
    m_split.plan = plan
    return m_split


def die_work_split(ops, coll, ctx, plan=None, mtp=False, batch=1):
    """power_scenarios.v41_die_workloads' per-stage op lists with the plan's scan shares moved to the helper stages
    (the scan and select ops of a split layer at the key shares of ctx positions), and the helper exchange's bytes on
    both ends' link energy (a switched traversal counted as two board hops, the ring hop too: conservative)."""
    plan = active_plan() if plan is None else plan
    if not plan:
        return ops, coll
    import arch_budget_v41 as A
    c = A._env()["c"]
    TOPK, CK = c["index_topk"], c["candidate_topk_blocks"]
    frac, start = {}, {}
    P = json.loads(A.PLACEMENT_REC.read_text())
    for st in P["stages"]:
        for l_ in st["layers"]:
            start.setdefault(l_["layer"], st["stage"])
    for L, helpers in plan.items():
        f0, fr = fractions(helpers, ctx, mtp, batch)
        home = start[L]
        mine = [(o, w) for o, w in ops[home] if o["name"] in SCAN_OPS and o.get("_layer") == L]
        if not any(fr) or not mine:
            continue
        ops[home] = [(o, w * (f0 if (o["name"] in SCAN_OPS and o.get("_layer") == L) else 1.0)) for o, w in ops[home]]
        for h, f in zip(helpers, fr):
            if f <= 0:
                continue
            ops[h["stage"]] = ops[h["stage"]] + [(o, w * f) for o, w in mine]
            by = 2 * (IDX_Q_BYTES + (TOPK + (CK if L == c["candidate_source_layer_id"] else 0)) * 8)
            coll[home] += by
            coll[h["stage"]] += by
    return ops, coll


# -- evaluation ----------------------------------------------------------------------------------------------------
def _dp():
    """The design point's pieces as tools/arch_lanes_v41.build composes them: sp, muts (wire included), hz, the lane
    split's mutation, the draft conditioning, the adopted collective levers' exposure mutations and terms."""
    import arch_lanes_v41 as AL
    import collective_exposure as CX
    import v41_collective_exposure as VX
    U, A = AL.U, AL.A
    d = AL.design_point()
    muts = [m for m in d["muts"] if m.__name__ != "stage_rebalance_split"]
    camp = json.loads(VX.CAMPAIGN.read_text())
    lev_camp = json.loads(VX.LEVERS_CAMPAIGN.read_text())
    dump = VX.dump_on_path(U, A, d["sp"], muts + [d["ml"]], d["hz"])
    dump_mtp = VX.dump_on_path(U, A, d["sp"], muts + [d["ml"]], d["hz"], positions=U.GAMMA + 1)
    lev = VX.recommended_exposure(dump, camp, lev_camp, dump_mtp=dump_mtp)
    lx = [CX.mutation(lev["terms"])] + ([CX.consumer_mutation(tuple(lev["consumers"]))] if lev["consumers"] else [])
    return dict(d, muts=muts, lx=lx, lev=lev)


def plan_muts(dp, plan, sp=None):
    return dp["muts"] + [split_mutation(plan, dp["lev"]["terms"]["hop"])] + [dp["ml"]] + dp["lx"]


def batch1(dp, plan, sp=None, contexts=None):
    import arch_latency_ladder_v41 as LX
    sp = sp or dp["sp"]
    out = {}
    for ctx in contexts or LX.CONTEXTS:
        r = LX.evaluate(sp, ctx, plan_muts(dp, plan), hz=dp["hz"], draft_extra_s=dp["draft_extra_s"])
        out[str(ctx)] = dict(ar=r["ar"], mtp=r["mtp"], T_us=r["T_us"], verify_us=r["verify_us"])
    return out


def points(dp, plan, sp=None, contexts=None):
    """The lanes record's operating points (b1, fill28, sat1024; with and without MTP) on the plan: per-user and
    aggregate rates (link-capped as arch_lanes_v41.build), stage busy, cycle and energy per token."""
    import arch_lanes_v41 as AL
    import arch_hbm_best_v41 as HB
    import v41_rack_design as RK
    LX, U, A = AL.LX, AL.U, AL.A
    sp = sp or dp["sp"]
    lev = dp["lev"]
    ms = plan_muts(dp, plan)
    dem = RK.stage_link_demand(RK.placement(), AL.rack_levers(lev), RK.residual_bytes())
    lanes = json.loads(AL.OUT.read_text())
    rom_static = lanes["static_w"]["rom_total"]
    out = {}
    for ctx in contexts or LX.CONTEXTS:
        rows = {}
        for ptag, bt in HB.POINTS:
            for mtp in (False, True):
                k = ptag + ("_mtp" if mtp else "")
                bt_ = A.point_batch(ptag, bt, ctx)
                hz = dp["hz"]
                with LX.clock(hz[0]), U.params(**hz[1]):
                    r_ = U.op_point(sp, ctx, bt_, mtp=mtp, levers=U.CHAIN_L3, muts=ms, units=U.POOLED_UNITS,
                                    draft_extra_s=dp["draft_extra_s"] if mtp else 0.0, contention=True)
                r_["cycle_s"] = r_["period_us"] * 1e-6
                lk = AL.link_cap(r_, dem, dp["split"], mtp)
                if lk["cap"] < 1.0:
                    r_["aggregate_tokens_s"] *= lk["cap"]
                    r_["tokens_s_per_user"] *= lk["cap"]
                    r_["cycle_s"] /= lk["cap"]
                e = HB.energy_point(sp, ctx, r_, U.LAYER_DIES, 28, LX.area(sp, U.MTP_M if mtp else 1), rom_static)
                sb = r_["stage_busy_us"]
                lay = [v for s, v in sb.items() if s != "head"]
                rows[k] = dict(batch=bt_, tokens_s_per_user=r_["tokens_s_per_user"],
                               aggregate_tokens_s=r_["aggregate_tokens_s"], period_us=r_["cycle_s"] * 1e6,
                               pass_T_us=r_["pass_T_us"], stage_busy_us=sb, busiest_stage=max(sb, key=sb.get),
                               busiest_over_mean=max(lay) / (sum(lay) / len(lay)), link_cap=lk["cap"],
                               energy_j=dict(dynamic=e["dynamic_j"], static=e["static_j"], total=e["total_j"]))
        out[str(ctx)] = rows
    return out


def switch_utilisation(plan, pts):
    """The busiest switch port (a package's 4 lanes, each direction) at every point: the helper exchange's switched
    legs (an 'up' helper's query, one copy per package; a 'down' helper's return, both dies' lists), the new index key
    a home group appends to a helper's range (68 B per position), and the Engram rows the port already carries on
    its consumer stages (results/arch/v41_rack.json traffic T3, split over the consumer groups' packages).  Per
    emitted token = positions per token x bytes; capacity 4 x the lane's net rate."""
    import arch_lanes_v41 as AL
    import arch_budget_v41 as A
    c = A._env()["c"]
    TOPK, CK = c["index_topk"], c["candidate_topk_blocks"]
    tau = json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())["tau"]
    rk = json.loads((ROOT / "results/arch/v41_rack.json").read_text())
    groups = [gr for gr in rk["logical"]["groups"] if gr.get("engram_layers")]
    engram_pkg = rk["traffic"]["per_token"]["T3_engram"]["bytes"] / max(1, 2 * len(groups))
    cap = AL.SWITCH * AL.LANE_NET_BPS
    start = {}
    for st in json.loads(A.PLACEMENT_REC.read_text())["stages"]:
        for l_ in st["layers"]:
            start.setdefault(l_["layer"], st["stage"])
    out = {}
    for ctx, rows in pts.items():
        o = {}
        for k, r in rows.items():
            pos = (AL.U.GAMMA + 1) / tau if k.endswith("_mtp") else 1.0
            port = {}                                        # (stage, 'rx'|'tx') -> bytes per position

            def add(stg, d, by):
                port[(stg, d)] = port.get((stg, d), 0.0) + by
            for gr in groups:
                add(gr["stage"], "rx", engram_pkg)
            for L, helpers in plan.items():
                f0, fr = fractions(helpers, int(ctx), k.endswith("_mtp"), r["batch"])
                ret = 2 * (TOPK + (CK if L == c["candidate_source_layer_id"] else 0)) * 8
                for h, f in zip(helpers, fr):
                    if f <= 0:
                        continue
                    if h["side"].startswith("up"):
                        add(start[L], "tx", IDX_Q_BYTES)
                        add(h["stage"], "rx", IDX_Q_BYTES)
                    elif h["side"] == "down":
                        add(h["stage"], "tx", ret)
                        add(start[L], "rx", ret)
                    add(start[L], "tx", 68 * f)                # the appended key, when it falls in the range
                    add(h["stage"], "rx", 68 * f)
            util = {f"S{s_}.{d}": by * pos * r["aggregate_tokens_s"] / cap for (s_, d), by in port.items()}
            worst = max(util, key=util.get)
            o[k] = dict(busiest_port=worst, utilisation=util[worst],
                        engram_only=engram_pkg * pos * r["aggregate_tokens_s"] / cap)
        out[ctx] = o
    return out


def power(pts, dp, plan, contexts=None):
    """Hottest-die power and its air / liquid verdict, array energy per token, at every point (tools/power_scenarios
    v41_points on this plan's rates and stage windows, scenario B)."""
    import power_scenarios as PS
    import arch_budget_v41 as A
    lad = json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())
    tau = lad["tau"]

    def rates(ctx):
        en = pts[str(ctx)]

        def win(k):
            e = en[k]
            t = tau if k.endswith("_mtp") else 1.0
            cyc_, st = t / e["tokens_s_per_user"] * 1e6, 28
            return {s: cyc_ / max(cyc_ / st, b) for s, b in e["stage_busy_us"].items()}
        return dict(ar=en["b1"]["tokens_s_per_user"], mtp=en["b1_mtp"]["tokens_s_per_user"],
                    sat_rate=en["sat1024"]["aggregate_tokens_s"], sat_batch=en["sat1024"]["batch"], sat_key=1024,
                    windows=dict(ar_batch1=win("b1"), mtp_batch1=win("b1_mtp")),
                    extra={"fill28": (28, False, en["fill28"]["aggregate_tokens_s"]),
                           "fill28_mtp": (28, True, en["fill28_mtp"]["aggregate_tokens_s"]),
                           "saturated_batch1024_mtp": (en["sat1024_mtp"]["batch"], True,
                                                       en["sat1024_mtp"]["aggregate_tokens_s"])})
    cfg = PS.load_cfg()
    if contexts:
        cfg["design_points"]["v41"]["contexts"] = list(contexts)
    with using(plan):
        rec = PS.v41_points(cfg, "B_proposed_production", V=A, rates=rates, tau=tau, gamma=lad["gamma"])
    lim = {k: PS.cooling_w(cfg, k, rec["dies_per_package"]) for k in ("air", "liquid")}
    static = sum(rec["die_static_w"].values())
    out = {}
    for ctx, rows in rec["per_context"].items():
        wins = rates(int(ctx))["windows"]
        o = {}
        for k, r in rows.items():
            w = r["hottest_die_w"]
            wf = wins.get(k) or {}
            o[k] = dict(rate=r["design_rate_tokens_s"], hottest_die=r["hottest_die"], hottest_die_w=w,
                        hottest_over_layer_mean=r["hottest_over_layer_mean"],
                        cooling=("air" if w <= lim["air"] else "liquid" if w <= lim["liquid"] else "exceeds liquid"),
                        air_capped_rate=r["cooling_classes"]["air"]["capped_rate"],
                        liquid_capped_rate=r["cooling_classes"]["liquid"]["capped_rate"],
                        energy_per_token_j=r["energy_per_token_j"], array_average_die_w=r["array_average_die_w"],
                        die_w_by_stage={s: static + j * r["design_rate_tokens_s"] * wf.get(s, 1.0)
                                        for s, j in r["die_dynamic_j_per_token_by_stage"].items()})
        out[ctx] = o
    return out, lim


def rack_input(pts):
    """Rack input watts at the rack's four scenarios (tools/v41_rack_design.power's wall chain: chips = the record's
    static total + dynamic J x aggregate; wall = (chips / VR + infrastructure) x (1 + CDU + fans) / PSU)."""
    rk = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]
    tech = json.loads((ROOT / "configs/hardware/technology.json").read_text())["power"]["rack_overheads"]
    ro = {k: (v["value"] if isinstance(v, dict) else v) for k, v in tech.items() if k != "purpose"}
    over = 1 + ro["cdu_fraction_of_it"] + ro["fan_fraction_of_it"]
    infra = sum(rk["infra_w"].values())
    e = pts["1048576"]
    out = {}
    for k, src in (("b1", "b1"), ("fill", "fill28"), ("fill_mtp", "fill28_mtp"), ("saturated_mtp", "sat1024_mtp")):
        dyn = e[src]["energy_j"]["dynamic"] * e[src]["aggregate_tokens_s"]
        chips = rk["static_total_w"] + dyn
        out[k] = dict(dynamic_w=dyn, rack_input_w=(chips / ro["vr_efficiency_48v_to_core"] + infra) * over
                      / ro["psu_efficiency"])
    return out


def evaluate(dp, name, plan, sp=None, sweep=True):
    b1 = batch1(dp, plan, sp)
    pts = points(dp, plan, sp)
    pw, lim = power(pts, dp, plan)
    row = dict(plan={str(L): hs for L, hs in plan.items()}, batch1=b1, points=pts, power=pw, cooling_limit_w=lim,
               rack=rack_input(pts), switch_lane_utilisation=switch_utilisation(plan, pts))
    if sweep:
        row["batch1_sweep"] = batch1(dp, plan, sp, SWEEP)
        extra = [c for c in POWER_SWEEP if str(c) not in pw]
        pws, _ = power(points(dp, plan, sp, extra), dp, plan, extra)
        allp = {**pw, **pws}
        row["cooling_sweep"] = {c: {k: dict(hottest_die=v["hottest_die"], hottest_die_w=v["hottest_die_w"],
                                            liquid=v["hottest_die_w"] <= lim["liquid"], air=v["hottest_die_w"] <= lim["air"])
                                    for k, v in allp[c].items()} for c in sorted(allp, key=int)}
    return row


def rom_feasibility(plan):
    """ROM a 'local' helper needs (the preceding layer's tail from the home stage + its copy of the layer's query
    front, per die) against what its dies can free (their Engram spill, re-spilled onto the other layer dies' spare,
    + their spare), from results/arch/v41_die_placement.json.  Layer bytes = the layers' total / 40 (the routed
    experts dominate every layer)."""
    import arch_budget_v41 as A
    c = A._env()["c"]
    P = json.loads(A.PLACEMENT_REC.read_text())
    out = {}
    layer_b = P["bytes"]["layers_total"] / c["num_layers"]
    for L, helpers in plan.items():
        for h in helpers:
            if h["side"] != "local":
                continue
            home = next(st for st in P["stages"] if any(l_["layer"] == L and l_["fraction"] > 0 for l_ in st["layers"]))
            tail = sum(l_["fraction"] for l_ in home["layers"] if l_["layer"] == L - 1)
            dies = [d for d in P["die_table"] if d["role"] == "layer" and d["stage"] == h["stage"]]
            spill = min(d.get("engram_spill_bytes", 0.0) for d in dies)
            spare = min(P["rom_bytes_per_die"] - d["weight_bytes"] - d.get("engram_spill_bytes", 0.0) for d in dies)
            front = front_rom_bytes(c, L)
            need = tail * layer_b / G + front["total"]
            left = P["engram_spill"]["layer_die_spare_total"] - P["engram_spill"]["onto_layer_dies"]
            out[f"L{L}->S{h['stage']}"] = dict(
                preceding_layer_tail_fraction_on_home=tail, tail_bytes_per_die=tail * layer_b / G,
                front_copy_bytes_per_die=front, need_bytes_per_die=need, helper_engram_spill_per_die=spill,
                helper_spare_per_die=spare, respill_bytes=G * max(0.0, need - spare),
                array_spare_left_after_spill=left, fits=need <= spill + spare and G * max(0.0, need - spare) <= left,
                change=("placement: the stage boundary moves so the helper holds all of layer %d, the helper carries "
                        "a copy of layer %d's query front, and its Engram spill moves to other layer dies" % (L - 1, L)))
    return out


def verdict(sc, base, needs):
    """The adoption rule on one scenario (user decisions 2026-09-28): the hottest die within the LIQUID limit at every
    operating point over the context sweep (air a sensitivity); the batch-1 autoregressive per-user rate not below the
    design point before rebalancing at any swept context; no hardware or ROM placement the design does not have; a
    gain in the fill / saturated aggregate.  The batch-1 MTP rate is reported against the same baseline
    (mtp_batch1_worst_ratio): where the liquid limit needs a helper in MTP verify passes it can cost a little."""
    sw, bs = sc["batch1_sweep"], base["batch1_sweep"]
    ar = min((sw[c]["ar"] / bs[c]["ar"], c) for c in sw)
    mtp = min((sw[c]["mtp"] / bs[c]["mtp"], c) for c in sw)
    gain = max(sc["points"][c][k]["aggregate_tokens_s"] / base["points"][c][k]["aggregate_tokens_s"]
               for c in sc["points"] for k in ("fill28", "fill28_mtp", "sat1024", "sat1024_mtp"))
    over = [(c, k, round(v["hottest_die_w"], 1)) for c, rows in sc["cooling_sweep"].items() for k, v in rows.items()
            if not v["liquid"]]
    ok_ar = ar[0] >= 1 - 1e-9
    return dict(batch1_worst_ratio_over_sweep=min(ar[0], mtp[0]), ar_batch1_worst_ratio=ar[0], ar_batch1_worst_at=ar[1],
                mtp_batch1_worst_ratio=mtp[0], mtp_batch1_worst_at=mtp[1], batch1_not_slower=ok_ar and mtp[0] >= 1 - 1e-9,
                ar_batch1_not_slower=ok_ar, liquid_at_every_point=not over, over_liquid=over, needs=needs or None,
                best_aggregate_gain=gain, meets_rule=ok_ar and not over and not needs and gain > 1.0)


NEEDS = {"split_L20_S13_local": "ROM placement change (layer 19's tail onto S13, a copy of layer 20's query front)",
         "wide_select_128": "a 128-lane select unit on every layer and head die (area; RTL select unit width)"}
RECOMMENDED = "split_L20_S13_S12_r2_mtp"


def build():
    import arch_lanes_v41 as AL
    dp = _dp()
    rec = dict(schema=SCHEMA, tool="tools/v41_stage_rebalance.py", basis=__doc__.split("The levers")[0].strip(),
               levers=__doc__.split("The levers")[1].split("Every scenario")[0].strip(), adopted=ADOPTED,
               switched_one_way_s=switched_one_way_s(), sweep_contexts=list(SWEEP))
    with using({}):
        sc = {name: evaluate(dp, name, plan) for name, plan in PLANS.items()}
        # lever (iv): a 128-lane select unit on every die (+ its area on all 116 layer and head dies)
        wide = replace(dp["sp"], sel_lanes=dp["sp"].sel_lanes * 2)
        sc["wide_select_128"] = evaluate(dp, "wide_select_128", {}, sp=wide)
        a0, a1 = AL.LX.area(dp["sp"], 1), AL.LX.area(wide, 1)
        sc["wide_select_128"]["area_mm2_per_die"] = dict(design_point=a0, wide_select=a1, delta=a1 - a0)
    for name, row in sc.items():
        row["verdict"] = verdict(row, sc["baseline"], NEEDS.get(name))
        rf = rom_feasibility(PLANS.get(name, {}))
        if rf:
            row["rom_feasibility"] = rf
    rec["scenarios"] = sc
    # lever (iii): throttling to the cooling class is what the thermal caps already give (never a speed-up)
    rec["throttle"] = {n: {c: {k: dict(air=v["air_capped_rate"], liquid=v["liquid_capped_rate"], design=v["rate"])
                               for k, v in sc[n]["power"][c].items()} for c in sc[n]["power"]}
                       for n in ("baseline", RECOMMENDED)}
    ok = [n for n, r in sc.items() if r["verdict"]["meets_rule"]]
    rec["recommendation"] = dict(
        scenario=RECOMMENDED, meets_rule=RECOMMENDED in ok, passing=ok,
        why=("the only scenario with the rack as built that keeps the hottest die within the LIQUID limit at every "
             "operating point over the context sweep (user decision 2026-09-28) without slowing the batch-1 "
             "autoregressive rate.  Layer 20: two helper groups upstream of S14 (S13, then S12 with its return "
             "relayed by S13) hold its index keys from position 400,000 (S13, to 800,000) and 800,000 on (S12), "
             "engaged for users past 650,000 / 900,000; each gets the query through the switch port its packages "
             "already carry and returns its candidates on the ring.  Layers 2, 8 and 14 (ratio-2 scans, homes S1, S5, "
             "S9): the helper one stage upstream (S0, S4, S8) keeps a copy of their keys from 700,000 and scans it "
             "only in MTP verify passes -- in batches past 700,000, at batch 1 past 900,000 -- because a ratio-2 scan "
             "is too short to repay the round trip in an autoregressive pass (split_all_scans slows batch 1), while "
             "with MTP the home die exceeds liquid: at batch 1 past ~915K and in the saturated batch past ~750K. "
             "That costs the batch-1 MTP rate a little between 900K and ~1M (mtp_batch1_worst_ratio) -- the price of "
             "the liquid limit, which the throttle alternative would charge as the liquid cap instead (throttle).  "
             "split_L20_S13_S12 (layer 20 alone) never slows batch 1 but leaves S5 / S9 over liquid with MTP; the "
             "'local' helper needs a ROM placement change; the wider select needs an RTL width change and raises the "
             "hottest die's power."))
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    import v41_stage_rebalance as _mod      # one module instance: power_scenarios reads the active plan from it
    _mod.main()
