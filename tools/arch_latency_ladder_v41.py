#!/usr/bin/env python3
"""Push the DeepSeek-V4.1-Flash per-user rate further: attribute the remaining critical path of the recommended
design (docs/ARCH_SPEC_V41.md 13) at 1M (primary, user decision 2026-09-27) and 200K, and price every REALISTIC
microarchitecture / implementation lever as a cumulative ladder, with and without MTP (DSpark, measured tau 3.65), next to
the BEST HBM comparator at iso total logic area.  Model work only: the budget model (tools/arch_budget_v41.py) and
the utilisation study (tools/arch_utilization_v41.py) are imported, never edited.

    python3 tools/arch_latency_ladder_v41.py [--out results/arch/v41_latency_ladder.json]

Realism rules (the user's): best-shippable packaging (2-die packages, tensor group 4 across a package pair),
realistic links (130 ns light-FEC package hop, 10 ns UCIe), reticle-size dies with the stack counts that fit
(4 HBM3E stacks per die, 8 per 2-die package: user decision 2026-09-27), block areas inside the die's compute envelope (328.9 mm2, the analytical N5 figure; block areas
are ASAP7, so the check is conservative), clocks only where the slowest routed blocks close (or a named retime of
the few that do not).  The ladder stops where the next lever would need anything else.

Each lever is surgery on the budget model's solved DAG (arch_utilization_v41.solve) or a spec/clock change, and
carries its feasibility basis.  A lever is ADOPTED only if it does not slow batch 1 at 1M or 200K, with or
without MTP (user rule 2026-09-27).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_utilization_v41 as U  # noqa: E402

A, D = U.A, U.D
SCHEMA = "opentallas.v41-latency-ladder.v1"
OUT = ROOT / "results/arch/v41_latency_ladder.json"
CONTEXTS = (1048576, 200000)            # 1M is the primary context (user decision 2026-09-27)
TAU = U.TAU
ENVELOPE_MM2 = 328.9                    # per-die compute area of the analytical design (N5)
ADOPTED_COMM = ("replicate_a_proj", "direct_to_next_stage", "cut_through_hops", "ring_placement_return",
                "flat_one_shot", "oneshot_128_lanes")
SCAN_LAYERS_UNCAPPED = (2, 8, 14, 20)   # index-source layers: their scan grows with context (24-36 cap at 16,384)
# FP adds in each stream-op depth formula of decode_critical_path.v41_graph (FADD = 5 there); the spec's
# ot_hdc_fastfp adds are 3 cycles (routed 1,312 MHz, closed), so each costs 2 cycles too many in the DAG
FADDS = {"hc.rsqrt": 2, "hc.pre_post": 3, "hc_pre": 3, "norm.rsqrt": 2, "q_norm.rsqrt": 2, "kv_norm.rsqrt": 2,
         "cmp.norm.rsqrt": 2, "cmp.k_norm.rsqrt": 2, "norm.scale": 1, "q_norm.scale": 1, "kv_norm.scale": 1,
         "q_rope": 2, "kv_rope_qdq": 2, "cmp.pool": 3, "cmp.k_rope_qdq": 2, "cmp.row_qdq": 2, "idx.q": 2,
         "exp": 1, "sink": 2, "normalize": 2, "hc_post": 4, "bias": 1, "weights": 8, "shared_swiglu": 2,
         "swiglu": 2, "route_w": 1, "eng.gate": 3, "eng.add": 1}
DIVIDE_NODES = ("attn.normalize", "ffn.weights", "attn.cmp.pool", "ffn.softplus_sqrt")


@contextmanager
def clock(hz):
    """Price at another core clock: every cycle-denominated depth and width scales; link latencies (ns) do not."""
    if not hz:
        yield
        return
    E = A._env()
    old = (E["clock"], E["p"])
    E["clock"], E["p"] = hz, replace(E["p"], clock_hz=hz)
    try:
        yield
    finally:
        E["clock"], E["p"] = old


# -- the levers (mutations of the solved DAG) ------------------------------------------------------------------------------
def cyc():
    return 1.0 / A._env()["clock"]


def m_router_shared(g, sp):
    """The shared expert's w1|w3 waits only for its input xq, not for the router: with pooled engines the router
    runs on the BF16 pool and the shared expert on the block-dot pool, so the DAG's router -> shared_gu edge (the
    one-engine issue order) is not a data dependence."""
    for n, nd in g.nodes.items():
        if n.endswith("ffn.shared_gu"):
            nd["deps"] = [d for d in nd["deps"] if not d.endswith("ffn.router")]


def m_wide_head(g, sp):
    """The 4 lm_head dies get a 4x BF16 engine (they run nothing else; +56 mm2 on 4 dies, inside the envelope)."""
    for n, nd in g.nodes.items():
        if n.endswith("head.lm_head"):
            nd["issue"] /= 4


def m_idx_split(g, sp):
    """An uncapped index scan is split over 8 dies: the layer's own group and the neighbouring group (idle at batch
    1, same total work at any batch), each holding half of the layer's index keys in its HBM.  Costs one board hop
    to send the index query and one more board level in the top-k merge; applied only where it pays."""
    lk = A.links_for(A.BASELINE)
    rack = lk["rom_rack_cable_serdes"]["hop"] if "rom_rack_cable_serdes" in lk else lk["rom_board_serdes"]["hop"]
    extra = 2 * (rack + lk["rom_package_ucie"]["hop"])     # query hop + merge level over the rack cable
    for n, nd in g.nodes.items():
        m = re.match(r"L(\d+)\.attn\.idx\.(score|topk_local)$", n)
        if not m or int(m.group(1)) not in SCAN_LAYERS_UNCAPPED:
            continue
        score = g.nodes[f"L{m.group(1)}.attn.idx.score"]
        if score["issue"] / 2 <= extra:
            continue
        if m.group(2) == "score":
            if not nd.get("_split"):
                nd["issue"] /= 2
                nd["depth"] += extra
                nd["_split"] = True
        else:
            nd["issue"] /= 2


def m_fastfp(g, sp):
    """Formula-level fast FP: the DAG's stream-op depths count 5-cycle adds (FADD); the spec's are 3-cycle."""
    c2 = 2 * cyc()
    for n, nd in g.nodes.items():
        if nd["kind"] not in ("vector",):
            continue
        tail = re.sub(r"^(L\d+|E\d+|head)\.(attn|ffn)?\.?", "", n)
        k = FADDS.get(tail) or FADDS.get(".".join(tail.split(".")[-2:])) or FADDS.get(tail.split(".")[-1])
        if k:
            nd["depth"] = max(0.0, nd["depth"] - k * c2)


def m_radix4(g, sp):
    """Radix-4 IEEE divider (19 cycles, measured by the vector-unit agent) instead of ot_hdc_fdiv's 31."""
    for n, nd in g.nodes.items():
        if n.endswith(DIVIDE_NODES):
            nd["depth"] = max(0.0, nd["depth"] - 12 * cyc())


def m_me_tree(g, sp):
    """Matrix-engine output adder tree on the 3-cycle fast add: K me_tree is 6 cycles a level (5-cycle add + a
    register); 4 a level on ot_hdc_fastfp.  Levels = ceil(log2(blocks / 8)) of the node's K."""
    for n, nd in g.nodes.items():
        if nd["kind"] != "matvec" or n.endswith("hc.fn"):
            continue
        m = re.search(r"\[(\d+)[^,]*,\s*(\d+)\]", nd["desc"])
        if not m:
            continue
        k = int(m.group(2))
        lv = math.ceil(math.log2(max(1, math.ceil(k / 32) / 8)))
        nd["depth"] = max(0.0, nd["depth"] - 2 * lv * cyc())


def m_softplus_estrin(g, sp):
    """SENSITIVITY (not measured): sqrt(softplus) with its log polynomial evaluated by Estrin instead of Horner,
    taken as -40 cycles; needs a routed block before adoption."""
    for n, nd in g.nodes.items():
        if n.endswith("ffn.softplus_sqrt"):
            nd["depth"] = max(0.0, nd["depth"] - 40 * cyc())


def m_tp(G):
    """Tensor group G instead of 4 (dies per layer group): per-die issue of every split op x 4/G, every
    collective re-priced on the realistic fabric at span G (hierarchical: UCIe pair + board mesh of G/2 packages,
    best algorithm incl. one-shot), and the stage hops cut to the new number of groups.  A surgery approximation."""
    def f(g, sp):
        if G == 4:
            return
        E = A._env()
        fab = D.ArrayFabric(A.links_for(A.BASELINE), 2, "mesh", G)
        s = 4.0 / G
        for n, nd in g.nodes.items():
            k = nd["kind"]
            if k in ("matvec", "kvscan") and not n.endswith("hc.fn"):
                nd["issue"] *= s
            elif k == "select" and n.endswith("topk_local"):
                nd["issue"] *= s
            elif k == "collective":
                r = fab.collective(nd["op"], nd["payload"], G)
                red = D.FADD * math.ceil(math.log2(G)) / E["clock"] if nd["op"] != "all_gather" else 0.0
                nd["depth"], nd["issue"] = r["latency_s"] + red, r["bytes_s"]
        hops = [n for n, nd in g.nodes.items() if nd["kind"] == "hop" and nd["hop_kind"] == "substage"]
        keep = max(0, round(len(hops) * s))
        for n in hops[keep:]:
            g.nodes[n]["issue"] = g.nodes[n]["depth"] = g.nodes[n]["ctrl"] = 0.0
    f.__name__ = f"tp{G}"
    return f


L = U.lever_mutations()
COMM = [f for n in ADOPTED_COMM for f in L[n][0]] + [U.m_pool_idx]   # + the pooled indexer's measured depth


def _idx_limit(sp):
    keys = int(A.ROM_DIE_HBM_BPS / A.IDX_KEY_B / A._env()["clock"])   # what the die's stacks can feed
    w = float(max(keys * 4096, sp.weight_macs))
    return replace(sp, weight_macs=w, idx_macs=w, rom_bytes=w * A.FP8 + sp.bf16_macs * 2,
                   idx_bytes=min(keys * A.IDX_KEY_B, A.ROM_DIE_HBM_BPS / A._env()["clock"]))


def _x2(sp):
    w = A._with_widths(sp, {"weight": sp.weight_macs * 2, "bf16": sp.bf16_macs * 2, "su": sp.su_lanes * 2,
                            "sfu": sp.sfu_lanes * 2})
    return replace(w, idx_macs=w.weight_macs, att_macs=w.bf16_macs, idx_bytes=sp.idx_bytes)

# (key, label, kind, payload, feasibility)
#   kind: "mut" (a DAG mutation), "spec" (a spec transform), "clock" (Hz), "mtp" (dict m / gamma)
LADDER = [
    ("router_shared", "router || shared expert (drop the one-engine issue edge)", "mut", m_router_shared,
     "pooled engines (R-U2) put the BF16 router and the FP8 shared expert on different pools; shared_gu's data "
     "input is xq only (tools/hdc_golden_v41.py MoE order), so it may start with the router"),
    ("replicate_router", "router replicated on the 4 dies (no router all-gather)", "mut",
     L["replicate_router"][0][0],
     "3.9 MB/layer of BF16 gate on every die (+0.09% ROM); each die computes all 384 scores (53 cycles on the BF16 "
     "pool); was negative in 13.4 only because the router's 4x issue then delayed the shared expert"),
    ("wide_head", "4x BF16 engine on the 4 lm_head dies", "mut", m_wide_head,
     "the head dies run only the lm_head, argmax and draft rows; 4 x 18.8 mm2 on 4 dies (+56 mm2 in the array) "
     "fits their envelope; bytes are ROM-resident, read at 4x the rate (ROM macro capacity 828 KB/cycle vs 2x "
     "36,928 x 2 B = 148 KB/cycle)"),
    ("idx_split", "uncapped index scans split over 8 dies (own + neighbour group)", "mut", m_idx_split,
     "layers 2, 8, 14, 20 only: the neighbour group's indexer pool and HBM are idle while this group scans at "
     "batch 1 and do the same total work at any batch; half of the layer's index keys (68 B each) are written to "
     "the neighbour's HBM at compression time (capacity: KV lives in 4 of 28 groups, the rest have spare); costs "
     "a query hop and one more merge level, 2 x 140 ns"),
    ("idx_hbm_limit", "block-dot pool widened to the HBM key limit", "spec", _idx_limit,
     "the pooled block-dot engine widened to what the die's stacks can feed (stacks x 0.9 TB/s / 68 B per key x "
     "4,096 MACs a key); with 4 stacks that is 51 keys/cycle, below the pool's 61.6, so the scan is HBM-bound and "
     "the lever is empty"),
    ("seq_gap2", "sequencer issue gap 5 -> 2 cycles (pre-decoded queue)", "spec", lambda sp: replace(sp, seq_gap=2),
     "a pre-decoded instruction queue issues back to back; the replay (results/arch/v41x_replay.json) found a "
     "1-cycle issue worth 2.7 us; ot_rom_pkg_ctrl closes at 1,162 MHz"),
    ("fastfp_formulas", "3-cycle FP add in every stream-op depth (not only the chains)", "mut", m_fastfp,
     "rtl/hdc/ot_hdc_fastfp.sv (3-cycle add, routed 1,312 MHz, closed) is already the spec's add; the DAG's "
     "depth formulas still count 5-cycle adds in each op"),
    ("me_tree_fastfp", "matrix-engine output tree on the 3-cycle add", "mut", m_me_tree,
     "the same fast add in the weight/BF16 pools' block-sum tree: 4 cycles a level instead of 6"),
    ("radix4_div", "radix-4 IEEE divider (19 cycles) in normalize / route weights / pool / softplus", "mut",
     m_radix4, "measured by the vector-unit agent (docs/ARCH_SPEC_V41.md 6 item 2: IEEE divide 19 cycles, "
               "radix-4), bit-exact IEEE division, so the golden is unchanged"),
    ("sinkhorn_per_position", "one Sinkhorn unit per verified position (6 per die)", "params",
     dict(sinkhorn_units=0),
     "the MTP verify's 6 positions queue on one ot_hdc_sinkhorn per sublayer engine (6 rounds of ~42 unit clocks "
     "x 7 core cycles): 80 of the verify's 235 us at 1M are Sinkhorn; 6 units (33,091 um2 each, +0.2 mm2) run "
     "them at once; no effect at batch 1 without MTP"),
    ("hc_width", "HC projection widened until the MTP verify is within 0.2% of unlimited HC (1M)", "hcsize", None,
     "the HC projection stays a separate FP32 unit (~1,169 um2 per lane, fp32 add + mul pipes); once the chain and "
     "link levers shorten the sublayer body, its 126-cycle side branch surfaces on the 6-position verify path "
     "(spec agent, 2026-09-27); width chosen as the smallest power-of-two multiple of 1,024 lanes per weight lane "
     "within 0.2% of unlimited at 1M"),
    ("clock_1087", "core clock 1.034 -> 1.087 GHz (retime softplus, BF16 MAC, SFU lane)", "clock", 1.087e9,
     "the next-slowest routed token-path block is ot_hdc_tselect_w16 at 1,087 MHz; the three slower ones "
     "(softplus 1,034 closed, the BF16 MAC 1.03-1.05, the SFU lane 1,058 not closed) each take one more "
     "register stage (priced: +1 cycle is inside their depth margins); Sinkhorn stays a multicycle path"),
    ("widths_x2", "pooled engines x2 (block-dot, BF16, vector unit) inside the envelope", "spec", _x2,
     "2x the pooled block-dot and BF16 engines and the vector unit: at m = 2 the layer die's blocks are ~246 mm2 "
     "ASAP7, inside the 328.9 mm2 N5 compute envelope; the ROM read (2 x 326 KB/cycle) stays under the macros' "
     "828 KB/cycle; the key stream stays at the HBM limit"),
]
def m_hc_depth58(g, sp):
    """SENSITIVITY: the HC projection's depth at 58 cycles instead of the measured 126 (depends on the hcp agent's
    lane organisation; not measured)."""
    for n, nd in g.nodes.items():
        if n.endswith("hc.fn"):
            nd["depth"] = min(nd["depth"], 58 / A._env()["clock"])


SENSITIVITIES = [
    ("softplus_estrin", "sqrt(softplus) -40 cycles (Estrin, not measured)", m_softplus_estrin),
    ("hc_depth58", "HC projection depth 58 cycles instead of the measured 126 (not measured)", m_hc_depth58),
]


def rung_spec(base, upto):
    sp, muts, hz, prm = base, list(COMM), None, {}
    for key, _lab, kind, pay, _f in LADDER[:upto]:
        if kind == "mut":
            muts.append(pay)
        elif kind == "spec":
            sp = pay(sp)
        elif kind == "clock":
            hz = pay
        elif kind == "params":
            prm.update(pay)
        elif kind == "hcsize":
            sp = replace(sp, hc_macs=hc_size(sp, muts, (hz, prm)))
    return sp, muts, (hz, prm)


_HC = {}


def hc_size(sp, muts, hzp, ctx=1048576, tol=0.002):
    key = (sp.weight_macs, sp.bf16_macs, sp.su_lanes, len(muts), str(hzp))
    if key in _HC:
        return _HC[key]
    unl = evaluate(replace(sp, hc_macs=1e9), ctx, muts, hz=hzp)["mtp"]
    w = sp.hc_macs
    for cand in (6144.0, 8192.0, 10240.0, 12288.0, 16384.0, 24576.0, 32768.0):
        if cand < w:
            continue
        w = cand
        if evaluate(replace(sp, hc_macs=cand), ctx, muts, hz=hzp)["mtp"] >= (1 - tol) * unl:
            break
    _HC[key] = w
    return w


def evaluate(sp, ctx, muts, hz=None, m=2, gamma=5, tau=TAU, hbm=None, extra=(), draft_extra_s=0.0):
    """Batch-1 tokens/s per user without and with MTP (m-way core, gamma drafts, tau accepted).  draft_extra_s:
    seconds added to the draft on the MTP critical path (the conditioning transfer, tools/arch_lanes_v41.py)."""
    c = A._env()["c"]
    hz, prm = hz if isinstance(hz, tuple) else (hz, {})
    with clock(hz), U.params(**prm):
        muts = list(muts) + list(extra)
        ar = U.solve(sp, ctx, levers=U.CHAIN_L3, muts=muts, hbm=hbm)
        sm = replace(sp, lane_mult=m)
        v = U.solve(sm, ctx, positions=gamma + 1, levers=U.CHAIN_L3, muts=muts, hbm=hbm)
        d = A.draft_cost_s(sm, ctx, gamma, c, hbm=hbm)["total_s"] + draft_extra_s
    t = min(tau, gamma + 1)
    return dict(ar=1 / ar["period_s"], mtp=t / (v["period_s"] + d), T_us=ar["T_s"] * 1e6,
                verify_us=v["period_s"] * 1e6, draft_us=d * 1e6,
                breakdown_us={k: round(x, 3) for k, x in ar["breakdown_us"].items()})


def area(sp, m):
    return U.area_of(sp, A.unit_areas()[0], pooled=True, lm=m)["total"]


# -- attribution ---------------------------------------------------------------------------------------------------------
def attribution(sp, ctx, muts, positions=1):
    r = U.solve(replace(sp, lane_mult=2) if positions > 1 else sp, ctx, positions=positions, levers=U.CHAIN_L3,
                muts=muts)
    b = r["_built"]
    g = b.g
    rows = {}
    for n in g.path(b.sink):
        nd = g.nodes[n]
        key = nd["kind"] + ":" + re.sub(r"^(L\d+|E\d+|head)\.", "", n)
        row = rows.setdefault(key, dict(count=0, us=0.0, by_category={}))
        row["count"] += 1
        for k, v in g.contrib[n].items():
            row["us"] += v * 1e6
            row["by_category"][k] = row["by_category"].get(k, 0.0) + v * 1e6
    top = sorted(rows.items(), key=lambda kv: -kv[1]["us"])
    groups = {}
    for key, row in top:
        grp = ("index scan + select" if (".idx." in key or ".cand." in key or key.endswith("gather")) else
               "collectives" if key.startswith("collective") else
               "hops" if key.startswith("hop") else
               "weight / KV matvecs" if key.startswith(("matvec", "kvscan")) else
               "norms (sum of squares, rsqrt, scale)" if ("norm." in key) else
               "router chain (softplus, bias, top-6, weights)" if any(s in key for s in ("softplus", "bias", "top6",
                                                                                         "weights", "route_w")) else
               "attention softmax (max/exp/den/sink/normalize)" if any(s in key for s in (".exp", ".den", ".sink",
                                                                                          ".normalize", ".max")) else
               "other stream ops")
        groups[grp] = groups.get(grp, 0.0) + row["us"]
    return dict(T_us=r["T_s"] * 1e6, breakdown_us=r["breakdown_us"],
                groups_us=dict(sorted(groups.items(), key=lambda kv: -kv[1])),
                top_nodes=[dict(node=k, **{kk: (round(vv, 3) if isinstance(vv, float) else vv)
                                           for kk, vv in v.items() if kk != "by_category"},
                                by_category={kk: round(vv, 3) for kk, vv in v["by_category"].items() if vv > 1e-3})
                           for k, v in top[:30]])


# -- the best HBM comparator -------------------------------------------------------------------------------------------------
def best_hbm(sp, ctx, muts, hz, hb):
    """The HBM comparator with its own best choices on the same rung: the rung's generic levers (chain, links,
    depths, clock, sequencing), tensor-group width G in {4, 8, 16, 32} (all dies share the weight stream), and the
    MTP lane multiplier m in {2, 6}.  Its engines keep the ROM die's pooled spec (618 mm2 of logic: ample)."""
    hbm = dict(bw_Bps=hb["bw_Bps"], lat_s=hb["lat_s"], dies=hb["dies"])
    hbm_muts = [f for f in muts if f not in (m_wide_head, m_idx_split)]
    best = None
    rows = []
    for G in (4, 8, 16, 32):
        for m in (2, 6):
            r = evaluate(sp, ctx, hbm_muts + [m_tp(G)], hz=hz, m=m, hbm=hbm)
            rows.append(dict(G=G, m=m, ar=r["ar"], mtp=r["mtp"]))
    ar = max(rows, key=lambda x: x["ar"])
    mt = max(rows, key=lambda x: x["mtp"])
    return dict(ar=ar["ar"], ar_G=ar["G"], mtp=mt["mtp"], mtp_G=mt["G"], mtp_m=mt["m"], grid=rows)


def c7_exposure(sp, muts, hz):
    """Rack gate C7 / O2 on the ladder's top: every streaming collective and stage hop re-priced from its producer's
    last output with the RTL stage bench's measured tail (results/rtl/v41_stage_collective_campaign.json; terms
    derived against THIS graph's on-path nodes, tools/v41_collective_exposure.derive_terms).  The ladder prices
    collective bytes without the package's lane split; the headline with the adopted split is results/arch/
    v41_lanes.json design_point, which applies the same correction."""
    import collective_exposure as CX
    import v41_collective_exposure as VX
    camp = json.loads(VX.CAMPAIGN.read_text())
    dump = VX.dump_on_path(U, A, sp, muts, hz)
    terms, _rows = VX.derive_terms(camp, dump)
    out = dict(gate="C7 / O2", status="NOT MET (measured)", campaign=str(VX.CAMPAIGN.relative_to(ROOT)),
               campaign_binding={k: v for k, v in VX.campaign_binding(camp).items() if k != "source_sha256"},
               terms_residual_cycles={k: v["residual_cycles"] for k, v in terms.items()},
               note="ladder top without the lane split; the headline is results/arch/v41_lanes.json design_point")
    for ctx in CONTEXTS:
        r0 = evaluate(sp, ctx, muts, hz=hz)
        r1 = evaluate(sp, ctx, list(muts) + [CX.mutation(terms)], hz=hz)
        out[str(ctx)] = dict(overlap_assumed=dict(ar=r0["ar"], mtp=r0["mtp"]),
                             measured_exposure=dict(ar=r1["ar"], mtp=r1["mtp"], T_us=r1["T_us"],
                                                    breakdown_us=r1["breakdown_us"]))
    return out


def build():
    E = A._env()
    c = E["c"]
    spec = U.req_spec()
    base = U.unified(spec)                       # pooled engines (R-U2)
    hb = U.hbm_comparator(c)
    rec = dict(schema=SCHEMA, tool="tools/arch_latency_ladder_v41.py", clock_hz=E["clock"], tau=TAU,
               tau_band=U.TAU_BAND, gamma=5, primary_context=1048576,
               start="docs/ARCH_SPEC_V41.md 13.6 design point: spec + chain ladder L1-3 + R-U2..R-U8 (pooled engines, "
                     "adopted communication levers); HC 5,120 lanes/weight lane at its measured 126-cycle depth",
               realism=__doc__.split("Realism rules (the user's): ")[1].split("\n\nEach lever")[0].replace("\n", " "),
               envelope_mm2=ENVELOPE_MM2)
    rec["attribution"] = {str(ctx): dict(ar=attribution(base, ctx, COMM), mtp_verify=attribution(base, ctx, COMM, 6))
                          for ctx in CONTEXTS}
    # the ladder
    ladder = []
    prev = None
    for i in range(len(LADDER) + 1):
        sp, muts, hz = rung_spec(base, i)
        key, lab, kind, _p, feas = (("start", "13.6 design point", "", None, "") if i == 0 else LADDER[i - 1])
        row = dict(rung=i, key=key, lever=lab, feasibility=feas, area_mm2_m1=area(sp, 1), area_mm2_m2=area(sp, 2),
                   clock_hz=hz[0] or E["clock"], params=hz[1])
        for ctx in CONTEXTS:
            r = evaluate(sp, ctx, muts, hz=hz)
            h = best_hbm(sp, ctx, muts, hz, hb)
            row[str(ctx)] = dict(rom=r, hbm=dict((k, v) for k, v in h.items() if k != "grid"),
                                 rom_over_hbm_ar=r["ar"] / h["ar"], rom_over_hbm_mtp=r["mtp"] / h["mtp"])
            if prev:
                p = prev[str(ctx)]["rom"]
                row[str(ctx)]["gain_ar"] = r["ar"] / p["ar"] - 1
                row[str(ctx)]["gain_mtp"] = r["mtp"] / p["mtp"] - 1
        row["hbm_grid_1M"] = best_hbm(sp, 1048576, muts, hz, hb)["grid"] if i in (0, len(LADDER)) else None
        row["fits_envelope_m2"] = row["area_mm2_m2"] <= ENVELOPE_MM2
        adopted = i == 0 or all(row[str(ctx)].get(g, 0) >= -1e-4 for ctx in CONTEXTS for g in ("gain_ar", "gain_mtp"))
        gains = i > 0 and any(row[str(ctx)].get(g, 0) > 1e-3 for ctx in CONTEXTS for g in ("gain_ar", "gain_mtp"))
        row["adopted"] = adopted and row["fits_envelope_m2"] and (gains or i == 0)
        row["verdict"] = ("start" if i == 0 else "adopted" if row["adopted"] else
                          "no effect (not a requirement)" if adopted and row["fits_envelope_m2"] else
                          "outside the envelope" if not row["fits_envelope_m2"] else "slows batch 1: not adopted")
        ladder.append(row)
        if not row["adopted"] and i > 0:
            # drop a non-adopted lever from the cumulative set
            LADDER[i - 1] = (key, lab + " [NOT ADOPTED]", "none", None, feas)
        prev = row if row["adopted"] else prev
    rec["ladder"] = ladder
    # MTP tuning on the final rung: m (inside the envelope) and gamma (tau capped at gamma + 1)
    sp, muts, hz = rung_spec(base, len(LADDER))
    mt = []
    for m in (2, 3, 4):
        for gamma in (3, 5, 7):
            ok = area(sp, m) <= ENVELOPE_MM2
            row = dict(m=m, gamma=gamma, area_mm2=area(sp, m), fits=ok,
                       tau_note=f"tau {TAU:g} is the measured V4.1-Flash DSpark acceptance at gamma 5; at gamma 3 "
                                f"it is capped at 4; gamma 7 uses the same {TAU:g} (no measurement of a longer block's "
                                "gain)")
            for ctx in CONTEXTS:
                r = evaluate(sp, ctx, muts, hz=hz, m=m, gamma=gamma)
                row[str(ctx)] = dict(mtp=r["mtp"], verify_us=r["verify_us"], draft_us=r["draft_us"])
            mt.append(row)
    rec["mtp_tuning"] = mt
    # spending the area: wider pooled engines at m = 2, or the rung before them at a larger m
    sp_pre, muts_pre, hz_pre = rung_spec(base, len(LADDER) - 1)
    mw = []
    for tag, s_, m in (("x1, m=2", sp_pre, 2), ("x1, m=3", sp_pre, 3), ("x1, m=4", sp_pre, 4), ("x2, m=2", sp, 2)):
        row = dict(config=tag, m=m, area_mm2=area(s_, m), fits=area(s_, m) <= ENVELOPE_MM2)
        for ctx in CONTEXTS:
            r = evaluate(s_, ctx, muts_pre, hz=hz_pre, m=m)
            row[str(ctx)] = dict(ar=r["ar"], mtp=r["mtp"])
        mw.append(row)
    rec["m_vs_width"] = mw
    # sensitivities on the final rung
    sens = {}
    for key, lab, f in SENSITIVITIES:
        sens[key] = dict(label=lab, **{str(ctx): evaluate(sp, ctx, muts + [f], hz=hz) for ctx in CONTEXTS})
    for tau in U.TAU_BAND:
        sens[f"tau_{tau}"] = {str(ctx): evaluate(sp, ctx, muts, hz=hz, tau=tau)["mtp"] for ctx in CONTEXTS}
    for G in (8,):
        sens[f"rom_tp{G}"] = {str(ctx): evaluate(sp, ctx, muts + [m_tp(G)], hz=hz) for ctx in CONTEXTS}
    rec["sensitivities"] = sens
    rec["final_attribution_1M"] = attribution(sp, 1048576, muts)
    rec["c7_measured_exposure"] = c7_exposure(sp, muts, hz)
    rec["stop"] = ("the ladder stops at the envelope: beyond it are a 4-die package (option c, ~2028+), a sub-100 ns "
                   "board link (no FEC-free 112G board-reach standard), clocks past the 1,087-1,123 MHz routed "
                   "blocks (every stream lane, select and link endpoint would need retiming), or the rejected norm "
                   "folding (changes the FP8 quantisation point)")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: None) + "\n")
    for r in rec["ladder"]:
        x, y = r["1048576"], r["200000"]
        print(f"{r['rung']:2d} {r['key']:18s} {'A' if r['adopted'] else '-'} 1M {x['rom']['ar']:7.0f} "
              f"{x['rom']['mtp']:7.0f} | HBM {x['hbm']['ar']:6.0f} {x['hbm']['mtp']:6.0f} | x{x['rom_over_hbm_ar']:.2f} "
              f"x{x['rom_over_hbm_mtp']:.2f} || 200K {y['rom']['ar']:7.0f} {y['rom']['mtp']:7.0f} "
              f"| {r['area_mm2_m2']:.0f} mm2")
    x = rec["c7_measured_exposure"]
    print("C7 measured exposure on the top rung:", {c: (round(x[c]["measured_exposure"]["ar"]),
                                                         round(x[c]["measured_exposure"]["mtp"])) for c in ("1048576", "200000")})


if __name__ == "__main__":
    main()
