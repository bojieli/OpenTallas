#!/usr/bin/env python3
"""HBM-PRICE5 (10-18): numerics-preserving options to win back the d4g cross-quadrant gather cost, priced on the
HBM-B-RTL3 d4g pricer (hgi_sim.d4g_quadrant_1017: plan_study machinery + quadrant placement + static-schedule adders).

BASE = the adopted d4g (coordinator 0dr): two rings + QBG (quantize-before-gather, bit-exact bench PASS) on every
d4g adder (AG, XQT, D2, SU, SFUD, SFUC, BD; RTL1/2 ledger latencies).  Every option keeps the golden rounding points
and reduction orders (owner 10-18 03:50: accept the loss rather than change numerics); options that would reorder a
sum (K-split w2 / wo_b with partial sums, per-quadrant partial moe_sum) or lower precision (FP8 on a gather whose
consumer is not an FP8 linear) are excluded.

OPTIONS (knob `p5` on the d4g knob; cost transforms on top of d4g_quadrant_1017.d4g_added):
 (1) EP  expert-parallel inside the die: expert slot k's w1 / w3 / w2 die slices all live in ONE quadrant q(k), so the
     expert-intermediate gather is addressed by the sender dies to quadrant q(k)'s COLL endpoint only (one delivery
     lane: + 3 D, D = (G - 1) f / 4 lanes) and never enters the ring (AG = 0).  The quadrant runs the slot on its 4 SMs:
     rows per SM R = ceil(m_die / 16) -> R' = ceil(m_die / 4) (w1 / w3: m_die = 2304 / 192 = 12 -> 1 -> 3; w2: 5120 / 192
     = 27 -> 2 -> 7), cost c' = (R' / R) c (the native expert records, weights staged in SMEM, cost 32.6 / 43.6
     cycles at AR: no fixed part is assumed, the conservative bound).  The four quadrants run
     different slots at once: the serial SM-unit model is charged share = n_max / n_slots of each slot record
     (n_slots = the layer's expert-slot instances incl. the shared expert; AR 7, MTP P = 6 the union slots + shared).
     moe_sum (golden order e0 + e1, + e2 + e3, ...) gathers the die's e_k.d rows (27 x 4 B a slot) from their quadrants:
     + 1 XQ crossing per moe_sum record.  COLL records stay serial (the base convention; no credit for overlapping
     four quadrant gathers) EXCEPT the delivery lane occupancy: slot k's whole gather rides quadrant q(k)'s lane (4 D)
     while the other lanes carry other slots, so the record pays 4 D x n_max / n_slots - D (ep_serial_coll: + 3 D).
       ep_repl   every expert's die slice REPLICATED in all 4 quadrants (x4 expert bytes), slot k -> quadrant k mod 4
                 (compile-time, routing-independent): n_max = ceil(n_slots / 4)  [static-schedule legal]
       ep_part   experts PARTITIONED by id (no replication).  A static schedule must reserve the worst case: all routed
                 slots of a position in one quadrant (measured max 6 of 6, ep_quadrant_stats.json): n_max = n_slots - 1
       ep_part_mean  information only (needs a routing-dependent schedule = forbidden): n_max = measured mean
 (2) CM  collective matmul, K-ordered: an SM linear fed by a gathered C1 operand (QBG_TAGS consumers: w2, wo_b,
     engram.wkv) is issued at its static slot BEFORE the remote quarters land and streams the quarters in the golden K
     order (quarter 0 first; the ring injects the quarters in K order), so the FP32 accumulation order is unchanged.
     It can hide at most 3/4 of its own K stream (c_cons = the consumer record's base cost) under the SERIALISATION part
     of the exposed gather: hidden = min(ser_exposed, 0.75 c_cons).  The hop latency is never hidden (the last quarter
     still has to arrive).  An UPPER bound (it assumes the K-ordered injection costs no extra ring time).  Rotating the K
     order to start on the local quarter would reorder the FP32 sum: excluded.  Buffer: one quarter of the operand a
     position staged at the x-load (FP8 codes + 1/32 scales).
 (3) MESH 2x2 full mesh: diagonal COLL links coll_SW<->coll_NE, coll_SE<->coll_NW (Manhattan 9.1-9.3 mm = 2 ring
     edges -> 2 r relay stages).  Direct all-gather on the mesh: each quadrant sends its quarter to the 3 others at once.
       mesh_1w   ring A (1 x 280 b / direction) + 1-wide diagonals (replaces ring B; same bit-mm as two rings):
                 AG = min(ring-1 schedules, F + hop_d)
       mesh_2w   two rings + 2-wide diagonals: min(ring-2 schedules, ceil(F / 2) + hop_d)
       r2d_1w    two rings + 1-wide diagonals: edges 2 lanes, diagonal 1 lane; the diagonal destination's quarter is
                 split diagonal / 2-hop over the edges: t = 2 F / 3 (edge load 2 F - t = 2 t): ceil(2F/3) + max(hop_d, 2 hop)
     hop = 2 + r, hop_d = 2 + 2 r (r = COLL_RING stages).
 (4) RINGS k = 3, 4 (each ring is already bidirectional: CW + CCW 280 b a link, MODE 0 / MODE 1): flits split over k.
 (5) RECOMPUTE the o-group producer per quadrant: every quadrant COLL engine receives all 8 contributors' FULL partial
     (not its quarter) and reduces them in the golden tree order itself -> no ring AG, 4x ingress (+ 3 D).  Router /
     wq_a / wkv producers are split over 192 dies (2-12 rows a die), so a per-quadrant recompute would re-read the full
     weight matrix (e.g. router 384 x 5120: ~10k cycles at a quadrant's 4 PCs) -- not priced as viable.

    PYTHONPATH=tools python3 -m hgi_sim.d4g_price5_1018 --out results/arch/hbm_d4g_price_1017/price5/price5.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import multiprocessing as mp
import re
from pathlib import Path

from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_die_split as S
from hgi_sim import ds_relay_latency as RL
from hgi_sim import ds_mtp_verify as V
from hgi_sim import timing as T

CLK = Q.CLK
ROOT = Q.ROOT
SLOT_RE = re.compile(r"^expert slot (\d+) (w[123])")
EG_RE = re.compile(r"^expert_intermediate_gather\.s(\d+)")
HIDDEN, INTER, G1, NSM, SPQ = 5120, 2304, 192, 16, 4
M_DIE = {"w1": math.ceil(INTER / G1), "w3": math.ceil(INTER / G1), "w2": math.ceil(HIDDEN / G1)}
K_DIM = {"w1": HIDDEN, "w3": HIDDEN, "w2": INTER}
WBYTES = 0.5 + 1 / 32               # FP4 expert weights + one UE8M0 scale byte a 32-block
SM_BW = 99.0                        # B / cycle / SM (owner 10-12)
EP_STATS = ROOT / "results/arch/hbm_d4g_price_1017/price5/ep_quadrant_stats.json"

_SLOTS = {}                         # layer -> number of expert-slot instances (filled per compiled programme)
_ORIG_ADDED = Q.d4g_added
_ORIG_COMPILE = RL.compile_case
_CM_LOG = {}


def _count_slots(prog):
    _SLOTS.clear()
    for r in prog:
        if r.unit == "SM" and SLOT_RE.match(r.tag or "") and (r.tag or "").endswith("w1"):
            L = getattr(r, "layer", -1) if isinstance(getattr(r, "layer", -1), int) else -1
            _SLOTS[L] = _SLOTS.get(L, 0) + 1


def compile_case(case):
    prog = _ORIG_COMPILE(case)
    _count_slots(prog)
    _consumers(prog)
    return prog


RL.compile_case = compile_case


def topo_ag(B, kn, D):
    """(exposed cycles, its serialisation part) of the on-die all-gather of B bytes for the configured cross-quadrant
    topology (module doc 3 / 4); the hop part is pure latency"""
    p = kn["p5"]
    r = kn["r_hop"]
    nom = kn["nominal"]
    topo = p.get("topo", "ring")
    rings = p.get("rings", kn.get("rings", 1))
    hop, hop_d = 2 + r, 2 + 2 * r

    def ring(k):
        F = -(-B // Q.NQ // (Q.RING_FLIT_B * k))
        return [(math.ceil(1.5 * F), 3 * hop), (2 * F, 2 * hop)]      # MODE 0 / MODE 1 (d4g_quadrant_1017.ag_cycles)
    F1 = -(-B // Q.NQ // Q.RING_FLIT_B)                                 # flits a quadrant on ONE 256-b lane
    if topo == "ring":
        cand = ring(rings)
    elif topo == "mesh_1w":
        cand = ring(1) + [(F1, hop_d)]
    elif topo == "mesh_2w":
        cand = ring(2) + [(math.ceil(F1 / 2), hop_d)]
    elif topo == "r2d_1w":
        cand = ring(2) + [(math.ceil(2 * F1 / 3), max(hop_d, 2 * hop))]
    else:
        raise KeyError(topo)
    best = None
    for ser, lat in cand:
        se = max(0.0, ser - D) if nom else ser
        if best is None or se + lat < best[0]:
            best = (se + lat, se)
    return best


_CONS = {}                          # (layer, tag) of a C1 gather -> base cost of its SM consumer (compile hook)


def _consumers(prog):
    """(2) the first later SM record that reads a C1 gather's result, and its base cost (no d4g adders)"""
    _CONS.clear()
    base = Q._PREV(None)
    for i, r in enumerate(prog):
        if Q.classify(r) != "C1" or not (r.tag or "").startswith(Q.QBG_TAGS):
            continue
        w = set(getattr(r, "writes", ()) or ())
        for x in prog[i + 1:i + 40]:
            if x.unit == "SM" and w & set(getattr(x, "reads", ()) or ()):
                L = getattr(x, "layer", 0) if isinstance(getattr(x, "layer", 0), int) else 0
                try:
                    c = base(x, T.Dyn(V.DT.POS), L)[0]
                except Exception:
                    c = 0.0
                _CONS[(getattr(r, "layer", None), r.tag)] = c
                break


def cm_overlap(r, ser_exposed, n_q):
    """(2) collective matmul, K-ordered: the consumer streams the quarters in the golden K order as they complete, so
    at most 3/4 of its K stream runs under the serialisation tail of the gather (hop latency is never hidden).
    Returns (hidden cycles, per-quadrant staging bytes: one quarter of the operand a position, FP8 codes + scales)."""
    cc = _CONS.get((getattr(r, "layer", None), r.tag), 0.0)
    hid = min(ser_exposed, 0.75 * cc)
    A = r.desc.get("A")
    n = A.n if A is not None else 0
    return hid, n_q * (n / Q.NQ) * (1 + 1 / Q.QBG_BLOCK)


def ep_share(r, p):
    """n_max / n_slots of the record's layer for the EP placement p['ep'] (module doc 1)"""
    L = getattr(r, "layer", -1) if isinstance(getattr(r, "layer", -1), int) else -1
    n = _SLOTS.get(L, 7)
    ep = p["ep"]
    if ep == "repl":
        nmax = math.ceil(n / Q.NQ)
    elif ep == "part":
        nmax = max(1, n - 1)
    else:                                                   # measured mean max-per-quadrant (+ the shared slot)
        nmax = min(n, (p["ep_mean_ar"] if n <= 7 else p["ep_mean_mtp"]) + 1)
    return nmax / n


def d4g_added5(r, c, kn):
    p = kn.get("p5")
    if not p:
        return _ORIG_ADDED(r, c, kn)
    on = set(kn["on"])
    kn2 = dict(kn, on=on - {"AG"})
    add = _ORIG_ADDED(r, c, kn2)
    tag = r.tag or ""
    cl = Q.classify(r)
    xq = 1 + kn["xq"]
    ep = p.get("ep")
    if "AG" in on and cl == "C1" and c > 0:
        B, wire = Q.coll_bytes(r)
        if kn.get("ag_qbg") and Q.qbg_ok(r):
            B = B // Q.VM_WORD_B + B // Q.VM_WORD_B // Q.QBG_BLOCK
        f1 = max(1, math.ceil(wire / kn["G1"] / 64))
        D = S.deliver(f1, kn["G1"], kn["lanes"])
        if ep and EG_RE.match(tag):
            # the whole slot on its quadrant's lane (4 D), no ring; the 4 quadrant lanes carry different slots at once
            # (share n_max / n_slots), unless ep_serial_coll (the serial-COLL convention: + 3 D a slot)
            if p.get("ep_serial_coll"):
                add += 3 * D
            else:
                add += 4 * D * ep_share(r, p) - D
        elif p.get("ogroup_recompute") and tag.startswith("o-group"):
            add += 3 * D
        else:
            ag, se = topo_ag(B, kn, D)
            a, se = (ag, se) if not kn.get("allow_mcast", True) or ag <= 3 * D else (3 * D, 3 * D)
            if p.get("cm") and tag.startswith(Q.QBG_TAGS):
                npos = (getattr(r, "npos", 1) or 1) if (getattr(r, "mtp_kind", "") or "") in ("shared", "egather") else 1
                hid, buf = cm_overlap(r, se, npos)
                a -= hid
                k = re.sub(r"\s.*", "", tag)
                e = _CM_LOG.setdefault(k, dict(n=0, hidden=0.0, buf_max=0.0))
                e["n"] += 1
                e["hidden"] += hid
                e["buf_max"] = max(e["buf_max"], buf)
            add += a
    if ep and r.unit == "SM":
        m = SLOT_RE.match(tag)
        if m:
            w = m.group(2)
            # the native expert records (weights staged in SMEM by expert_fetch) cost 32.6 / 43.6 cycles: no HBM first
            # access to amortise, so the WHOLE record scales with the per-SM rows (conservative: no fixed part)
            R = -(-M_DIE[w] // NSM)
            R1 = -(-M_DIE[w] // SPQ)
            c1 = c * R1 / R
            add += c1 * ep_share(r, p) - c
    if ep and tag.startswith("moe_sum"):
        add += xq
    return add


Q.d4g_added = d4g_added5


def _any(job):
    return Q._any(job)


def ep_capacity():
    """(1) per-die / per-quadrant HBM bytes of the routed + shared expert slices (TP-192, FP4 + UE8M0 / 32)"""
    c = json.loads((ROOT / "compiler/models/deepseek-v4.1-flash/config.json").read_text())["text_config"]
    per_exp = 3 * c["hidden_size"] * c["moe_intermediate_size"]
    n = c["n_routed_experts"] + c["n_shared_experts"]
    tot = per_exp * n * c["num_hidden_layers"] * WBYTES
    die = tot / G1
    stack = 22.5e9
    return dict(expert_params_total=per_exp * n * c["num_hidden_layers"], expert_bytes_total=round(tot),
                expert_bytes_per_die=round(die), per_quadrant_partitioned=round(die / 4), per_quadrant_replicated=round(die),
                replication_extra_per_die=round(3 * die), die_hbm_bytes=2 * stack, die_hbm_usable_0p9=round(2 * stack * 0.9),
                quadrant_hbm_usable_0p9=round(stack / 2 * 0.9),
                note="d4g: 2 stacks x 22.5 GB (8 PCs each), quadrant = 4 PCs = half a stack")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=ROOT / "results/arch/hbm_plan_study_1017/stages.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    st = json.loads(a.stages.read_text())
    st["plan_b_bd"] = Q.bd_stages(st)
    led = Q.load_ledger()
    vb = PS.VARIANTS["b"]
    eps = json.loads(EP_STATS.read_text())["maps"]["freq"]
    epm = dict(ep_mean_ar=eps["ar_max_routed_per_quadrant"]["mean"], ep_mean_mtp=eps["mtp6_max_union_per_quadrant"]["mean"])
    base = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)

    def v(**p5):
        return (vb, dict(base, p5=dict(p5, _=1)))
    variants = {"b_plan": (vb, None), "d4g_2ring_qbg": (vb, base)}
    variants.update({
        "o1_ep_repl": v(ep="repl"),
        "o1_ep_part_static": v(ep="part"),
        "o1_ep_part_mean_info": v(ep="mean", **epm),
        "o1_ep_repl_serial_coll": v(ep="repl", ep_serial_coll=True),
        "o2_cm": v(cm=True),
        "o3_mesh_1w": v(topo="mesh_1w"),
        "o3_mesh_2w": v(topo="mesh_2w"),
        "o3_r2d_1w": v(topo="r2d_1w"),
        "o4_3ring": v(rings=3),
        "o4_4ring": v(rings=4),
        "o5_ogroup_recompute": v(ogroup_recompute=True),
        "c12_ep_cm": v(ep="repl", cm=True),
        "c14_ep_4ring": v(ep="repl", rings=4),
        "c24_cm_4ring": v(cm=True, rings=4),
        "c23_cm_mesh2w": v(cm=True, topo="mesh_2w"),
        "c124_ep_cm_4ring": v(ep="repl", cm=True, rings=4),
        "c1245_all_ring4": v(ep="repl", cm=True, rings=4, ogroup_recompute=True),
        "c1235_all_mesh2w": v(ep="repl", cm=True, topo="mesh_2w", ogroup_recompute=True),
    })
    if a.only:
        keep = set(a.only.split(","))
        variants = {k: x for k, x in variants.items() if k in keep or k == "b_plan"}
    jobs = [("ds", f"{k}|{case}", case, v_, st, kn) for k, (v_, kn) in variants.items()
            for case in ("AR", "MTP_design", "draft_design")]
    jobs += [("qwen", f"{k}|qwen", v_, st, kn) for k, (v_, kn) in variants.items()]
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.map(_any, jobs, chunksize=1))
    dref = json.loads((ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json").read_text())
    smt = dref["smallest_meeting_target"]["fixed"]
    mh_ctl = smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]
    table = {}
    for k in variants:
        ar = res[f"{k}|AR"]["cycles"]
        d = res[f"{k}|draft_design"]
        step = res[f"{k}|MTP_design"]["cycles"] + d["draft_cycles"] + d["seed_cycles"] + mh_ctl
        table[k] = dict(ar_cycles=round(ar, 1), ar_tok_s=round(CLK / ar, 1), mtp_step_cycles=round(step, 1),
                        mtp_design_tok_s=round(V.TAU * CLK / step, 1), qwen_tok_s=res[f"{k}|qwen"]["tok_s"])
    b = table["b_plan"]
    d0 = table.get("d4g_2ring_qbg")
    for t in table.values():
        for x, y in (("ar", "ar_tok_s"), ("mtp", "mtp_design_tok_s"), ("qwen", "qwen_tok_s")):
            t[f"d_{x}_pct_vs_b_plan"] = round(100 * (t[y] / b[y] - 1), 2)
            if d0:
                t[f"d_{x}_pct_vs_d4g"] = round(100 * (t[y] / d0[y] - 1), 2)
    # (2) buffer census on the AR programme (one process: recompute the AR schedule with cm on)
    out = dict(schema="opentallas.hbm_d4g_price5.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, base_knob={k: (sorted(x) if isinstance(x, set) else x) for k, x in base.items()},
               variants={k: (x[1] or {}).get("p5") for k, x in variants.items()},
               table=table, ep_capacity=ep_capacity(), ep_mean_used=epm)
    print(json.dumps(dict(table=table), indent=1, default=str))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


def cm_census(case="AR"):
    """(2) per C1 tag: AG cycles hidden under the consumer prefix and the per-quadrant prefetch buffer (one schedule)"""
    st = json.loads((ROOT / "results/arch/hbm_plan_study_1017/stages.json").read_text())
    st["plan_b_bd"] = Q.bd_stages(st)
    base = dict(Q.knob(Q.ADDERS, st, ledger=Q.load_ledger()), rings=2, ag_qbg=True, p5=dict(cm=True))
    _CM_LOG.clear()
    r = Q._job(("cm", case, PS.VARIANTS["b"], st, base))[1]
    return dict(cycles=r["cycles"], per_tag={k: dict(n=v["n"], hidden_cycles=round(v["hidden"], 1),
                                                     buffer_bytes_per_quadrant_max=round(v["buf_max"]))
                                             for k, v in sorted(_CM_LOG.items())})


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cm-census":
        print(json.dumps(dict(AR=cm_census("AR"), MTP_design=cm_census("MTP_design")), indent=1))
        raise SystemExit(0)
    raise SystemExit(main())
