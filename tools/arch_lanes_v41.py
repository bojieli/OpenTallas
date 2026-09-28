#!/usr/bin/env python3
"""V4.1 ROM array: the package's 112G lane split priced per collective, and SerDes static power in the energy ratios.
Model work only; imports the ladder (tools/arch_latency_ladder_v41.py) and the best-comparator record.

    python3 tools/arch_lanes_v41.py [--out results/arch/v41_lanes.json]

Rack study conflicts (agent a84f863e, results/arch/v41_rack.json on its branch at 5aa3bba1):

C8  A 2-die package has 90 lanes of 112G PAM4 (1.19 TB/s per direction, 13.18 GB/s net per lane,
    technology.json).  The rack allocates TP 32 (each die 2 x 8 lanes to the two dies of the partner package,
    105 GB/s per die pair), stage 24 out + 24 in, switch 4, spare 6.  Every collective's bytes are therefore priced
    per PEER link: a one-shot all-reduce sends the die's whole partial to each peer (the remote ones in parallel on
    their own lanes, 105 GB/s each at TP 32), an all-gather sends the die's quarter; the in-package peer is UCIe
    (4.2 TB/s).  The bytes still chase their producer (overlapped reductions), so they cost time only where they
    outlast it -- the DAG decides.  A stage hop's 41 KB residual crosses on the 2 packages' stage lanes in parallel.
    The search: TP lanes t in multiples of 4 (2 peers x 2 dies), stage = (90 - 4 switch - 6 spare - t) / 2 each way.
C4  SerDes static power: 84 always-on lanes per layer/head package at 0.728 W each (6.5 pJ/bit at 112 Gb/s) = 61 W
    per package, 30.6 W per die; the 72 Engram table dies carry 1 lane each (2 per package, 0.728 W per die).  The
    switched HBM comparator's SerDes is charged on its own fabric (tools/arch_hbm_switched_v41.serdes_w_per_die: the
    lanes that carry 0.9 TB/s per direction per package).
C10 The 4 head dies carry 4 HBM3E stacks each for the drafter's per-user state (+16 x 2.8 W).

Design-point re-derivation (2026-09-28):
*   On-die wire: every registered traversal of the layer die (tools/v41_die_assembly.TRAVERSALS on its floorplan
    distances) is charged on its node's edges in the DAG (wire_mutation), on the ASAP7 routed-wire model; the
    150 ps/mm technology entry is a sensitivity and the no-wire point one ablation (record on_die_wire).
*   The MTP verify pass's stage hop carries its own bench-measured tail at its best measured T1 split
    (tools/v41_collective_exposure.mtp_hop_term, lever 5; record mtp_hop_split); the one-position hop keeps split20.
*   A saturated point holds at most the users the HBM holds after the capacity reserve (arch_budget_v41.point_batch).
*   The adopted split (R-L9) is kept unless another gains more than SPLIT_TOLERANCE.

Rack model gaps (closed here; results/arch/v41_rack.json gates C8 / C10):
*   The draft is conditioned on the inputs of target layers 37-39 at every verified position (DSpark
    dspark_target_layer_ids): 3 x 5,120 BF16 x 6 positions = 184 KB per verify step, which reach the head module
    over the S27 -> H stage link behind the residual.  Priced on the MTP critical path as a head hop's bytes
    (stage lanes of both packages + the UCIe half, the m_lanes rule) before the draft can start: draft_extra_s.
*   At batch > 1 with MTP the drafts of different users overlap on the head group; the aggregate points carry
    tools/arch_utilization_v41.draft_contention (conservative interference bound + unit throughput cap).
*   Every aggregate point is capped by its busiest package link (tools/v41_rack_design.stage_link_demand: the
    busiest stage's T1 link and UCIe link, and with MTP the head module's draft traffic): aggregate x
    min(1, 1 / the highest utilisation).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_hbm_best_v41 as HB  # noqa: E402

LX, U, A, D = HB.LX, HB.U, HB.A, HB.D
SCHEMA = "opentallas.v41-lanes.v1"
OUT = ROOT / "results/arch/v41_lanes.json"
CONTEXTS = LX.CONTEXTS
LANES = 90
LANE_NET_BPS = 13176470588.235294                  # the rack's lane_net_Bps (results/arch/v41_rack.json lanes)
SWITCH, SPARE = 4, 6
RACK_SPLIT = dict(tp=32, stage=24)
ADOPTED_SPLIT = dict(tp=52, stage=14, two_step=True)   # R-L9, the split the rack is cabled for
SPLIT_TOLERANCE = 0.005                               # a split must gain > 0.5% (1M, geometric mean) to replace it
UCIE_BPS = 4.2e12
LANE_W = 112e9 * 6.5e-12                           # 112 Gb/s x 6.5 pJ/b (technology.json energy.link_j_per_bit)
ACTIVE_LANES_PKG = 84
SERDES_W_DIE = ACTIVE_LANES_PKG * LANE_W / 2       # 30.58 W
TABLE_SERDES_W_DIE = LANE_W                        # 2 lanes per table package


def m_lanes(tp, stage, two_step=False):
    """Per-peer link bandwidth for every collective and stage hop (see the module doc).  two_step: an all-reduce
    whose one-shot bytes would outlast a board flight runs as a fixed-order reduce-scatter + all-gather instead
    (each peer gets 2 x n/4 instead of n; one more board flight and fold: still bit-identical on every die)."""
    b_peer = tp / 4 * LANE_NET_BPS
    b_stage = 2 * stage * LANE_NET_BPS             # the group's 2 packages send in parallel
    hop = A.links_for(A.BASELINE)["rom_board_serdes"]["hop"]

    def f(g, sp):
        mb = getattr(g, "mb", 1.0)
        fold = (2 + 3 * A.ADD_LAT["fastfp"]) / A._env()["clock"]
        for n, nd in g.nodes.items():
            if nd["kind"] == "collective":
                pay = nd["payload"] * mb
                G = nd.get("span") or 4
                per_peer = pay if nd["op"] == "all_reduce" else pay / G
                if two_step and nd["op"] == "all_reduce" and pay / (2 * b_peer) + hop + fold < pay / b_peer:
                    per_peer = pay / 2
                    nd["depth"] += hop + fold
                nd["issue"] = per_peer / b_peer
            elif nd["kind"] == "hop" and nd["hop_kind"] in ("stage", "substage", "head"):
                pay = nd["payload"] * mb
                nd["issue"] = pay / b_stage + pay / UCIE_BPS
    f.__name__ = f"lanes_tp{tp}_st{stage}" + ("_2step" if two_step else "")
    return f


WIRE_MODEL = "asap7_routed_fit"              # baseline (conservative); tech_global_wire (150 ps/mm) is the sensitivity
WIRE_SENSITIVITIES = ("tech_global_wire", "tech_global_wire_high")


def wire_mutation(model=WIRE_MODEL, sp=None):
    """Registered on-die traversals (tools/v41_die_assembly.TRAVERSALS) on the design-point DAG: every node that moves
    an operand across the layer die carries the traversal's cycles (floorplan distance / the wire model's per-cycle
    reach) as wire_in / wire_out latency on its edges (tools/decode_critical_path.Graph.solve, category
    'on_die_wire').  The DAG then charges only the traversals that are exposed on the critical path."""
    import v41_die_assembly as DA
    if sp is None:
        sp = _ladder_top()[0]
    geo = DA.traversal_geometry(sp)

    def m_wire(g, _sp):
        clk = A._env()["clock"]
        cyc = DA.traversal_cycles(geo, model, clk)
        s = 1.0 / clk
        far, half, coll = cyc["far_tile"] * s, cyc["spine_half"] * s, cyc["collective_edge"] * s
        ser, req = cyc["serdes_edge"] * s, cyc["hbm_request"] * s
        for name, nd in g.nodes.items():
            k = nd["kind"]
            if k == "matvec" and name.endswith("hc.fn"):
                nd["wire_in"], nd["wire_out"] = half, half          # the HC projection lives on the spine
            elif k in ("matvec", "kvscan"):
                nd["wire_in"], nd["wire_out"] = far, far
            elif k == "reduce":
                nd["wire_in"], nd["wire_out"] = half, half
            elif k == "select":
                nd["wire_in"] = half
            elif k == "collective":
                nd["wire_in"], nd["wire_out"] = coll, coll
            elif k == "hop":
                nd["wire_in"], nd["wire_out"] = ser, ser
            elif k == "op" and name.endswith(".gather"):
                nd["wire_in"] = req
    m_wire.__name__ = f"on_die_wire_{model}"
    m_wire.geometry = geo
    return m_wire


def splits():
    out = []
    for tp in range(8, LANES - SWITCH - SPARE, 4):
        st = (LANES - SWITCH - SPARE - tp) // 2
        if st >= 4:
            out.append(dict(tp=tp, stage=st, switch=SWITCH, spare=SPARE + (LANES - SWITCH - SPARE - tp - 2 * st)))
    return out


def _ladder_top():
    """The ladder's top rung with only the adopted levers (results/arch/v41_latency_ladder.json)."""
    base = U.unified(U.req_spec())
    adopted = {r["key"] for r in json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())["ladder"]
               if r["adopted"]}
    LX.LADDER[:] = [(k, lab, kind if k in adopted else "none", pay, f) for k, lab, kind, pay, f in LX.LADDER]
    return LX.rung_spec(base, len(LX.LADDER))


def conditioning_bytes():
    """Draft conditioning per verify step: the inputs of the DSpark target layers (37-39) at every verified position,
    BF16 (released config dspark_target_layer_ids; tools/v41_rack_design PHYS dspark_state)."""
    import v41_rack_design as RK
    c = A._env()["c"]
    layers = RK.PHYS["dspark_state"]["value"]["target_layers"]
    return len(layers) * c["hidden_size"] * 2 * (U.GAMMA + 1)


def conditioning_s(stage):
    """Seconds the conditioning bytes add before the draft can start: a head hop's bytes on the split's stage lanes
    (both packages in parallel) plus the per-die half over UCIe (the m_lanes rule for a stage/head hop); the hop's
    latency is already paid by the residual it rides behind."""
    pay = conditioning_bytes()
    return pay / (2 * stage * LANE_NET_BPS) + pay / UCIE_BPS


def design_point(split=None):
    """The adopted design point: the ladder's top with the chosen lane split (this tool's record, best_split if
    adopted else the rack's).  Returns sp, muts (without the lane pricing), hz, the split, its lane mutation and the
    draft-conditioning seconds of that split."""
    sp, muts, hz = _ladder_top()
    muts = list(muts) + [wire_mutation(sp=sp)]           # registered on-die traversals (ASAP7 routed-wire model)
    if split is None:
        rec = json.loads(OUT.read_text())
        split = rec["best_split"] if rec["best_adopted"] else rec["rack_split_result"]
    split = dict(tp=split["tp"], stage=split["stage"], two_step=split["two_step"])
    return dict(sp=sp, muts=list(muts), hz=hz, split=split, ml=m_lanes(split["tp"], split["stage"], split["two_step"]),
                draft_extra_s=conditioning_s(split["stage"]))


def rack_levers(lev):
    """The rack's lever dict (tools/v41_rack_design._levers) from this tool's in-process levers."""
    import v41_rack_design as RK
    return RK._levers(dict(bytes_scale=lev["bytes_scale"], picks=lev["picks"]))


def link_cap(point, dem, split, mtp):
    """Busiest package link at the point's aggregate (tools/v41_rack_design.link_utilisation) and the factor that
    caps the aggregate at 100% of it."""
    import v41_rack_design as RK
    cap_t1 = (split["tp"] // 4) * LANE_NET_BPS
    pos = (U.GAMMA + 1) / U.TAU if mtp else 1.0
    u = RK.link_utilisation(dem, point["aggregate_tokens_s"], pos, mtp, cap_t1, UCIE_BPS)
    worst = max(u, key=u.get)
    return dict(utilisation_uncapped=u, busiest_link=worst, cap=min(1.0, 1.0 / u[worst]),
                t1_link_Bps=cap_t1, ucie_Bps=UCIE_BPS, binds=u[worst] > 1.0)


def wire_attribution(sp, muts, hz, ctx=1048576, positions=1):
    """Exposed on-die wire on the solved critical path, by node kind (the traversal classes of
    tools/v41_die_assembly.TRAVERSALS), with the on-path counts; and the same traversals charged in full on every
    on-path node (the upper bound if nothing overlapped)."""
    with LX.clock(hz[0]), U.params(**hz[1]):
        sp_ = replace(sp, lane_mult=U.MTP_M) if positions > 1 else sp
        r = U.solve(sp_, ctx, positions=positions, levers=U.CHAIN_L3, muts=list(muts))
        g, sink = r["_built"].g, r["_built"].sink
        clk = A._env()["clock"]
        by, cnt, full = {}, {}, 0.0
        for n in g.path(sink):
            nd = g.nodes[n]
            w = g.contrib[n].get("on_die_wire", 0.0)
            full += nd.get("wire_in", 0.0) + nd.get("wire_out", 0.0)
            if w:
                k = "hc_projection" if n.endswith("hc.fn") else nd["kind"]
                by[k] = by.get(k, 0.0) + w * 1e6
                cnt[k] = cnt.get(k, 0) + 1
    return dict(exposed_us=sum(by.values()), exposed_us_by_kind=by, on_path_nodes_by_kind=cnt,
                exposed_cycles=sum(by.values()) * 1e-6 * clk, charged_in_full_us=full * 1e6, T_us=r["T_s"] * 1e6)


def build():
    E = A._env()
    sp, muts, hz = _ladder_top()
    WIRE = wire_mutation(sp=sp)
    muts_pre_wire = list(muts)
    muts = list(muts) + [WIRE]           # the adopted point carries its registered on-die traversals
    rec = dict(schema=SCHEMA, tool="tools/arch_lanes_v41.py", lanes_per_package=LANES, lane_net_Bps=LANE_NET_BPS,
               rack_split=RACK_SPLIT, basis=__doc__.split("Rack study conflicts")[1].strip())
    # the ladder's top without per-link bytes (as priced before), for reference
    ref = {str(ctx): LX.evaluate(sp, ctx, muts, hz=hz) for ctx in CONTEXTS}
    rec["ladder_top_overlap_assumed"] = {c: dict(ar=v["ar"], mtp=v["mtp"]) for c, v in ref.items()}
    grid = []
    for s0 in splits():
      for ts in (False, True):
        s = dict(s0, two_step=ts)
        row = dict(s)
        for ctx in CONTEXTS:
            r = LX.evaluate(sp, ctx, muts + [m_lanes(s["tp"], s["stage"], ts)], hz=hz,
                            draft_extra_s=conditioning_s(s["stage"]))
            row[str(ctx)] = dict(ar=r["ar"], mtp=r["mtp"], T_us=r["T_us"], verify_us=r["verify_us"],
                                 collective_bytes_us=r["breakdown_us"]["collective_bytes"],
                                 hops_us=r["breakdown_us"]["pipeline_hops"])
        grid.append(row)
    rec["grid"] = grid
    rack = next(r for r in grid if r["tp"] == RACK_SPLIT["tp"] and not r["two_step"])
    # the best split: highest 1M rate with MTP, then without; it must not be slower than the rack's anywhere
    key = lambda r: (math.sqrt(r["1048576"]["mtp"] * r["1048576"]["ar"]))  # noqa: E731
    best = max(grid, key=key)
    # the adopted split (R-L9) is kept unless another beats it by more than the model's resolution: the rack's cables,
    # lane map and figures follow it, and a sub-resolution gain is not a reason to re-cable
    inc = next(r for r in grid if all(r[k] == v for k, v in ADOPTED_SPLIT.items()))
    rec["split_resolution"] = dict(adopted=ADOPTED_SPLIT, tolerance=SPLIT_TOLERANCE,
                                   argmax=dict(tp=best["tp"], stage=best["stage"], two_step=best["two_step"]),
                                   argmax_gain_over_adopted=key(best) / key(inc) - 1)
    if key(best) <= key(inc) * (1 + SPLIT_TOLERANCE):
        best = inc
    ok = all(best[str(c)][k] >= rack[str(c)][k] * (1 - 1e-4) for c in CONTEXTS for k in ("ar", "mtp"))
    rec["rack_split_result"] = rack
    rec["best_split"] = best
    rec["best_adopted"] = ok
    chosen = best if ok else rack
    # the CONDITIONAL design point: every streaming collective / stage hop overlaps its producer (rack gate C7)
    rec["design_point_overlap_assumed"] = {str(c): dict(ar=chosen[str(c)]["ar"], mtp=chosen[str(c)]["mtp"])
                                           for c in CONTEXTS}
    # the ABLATION: the same point with the RTL stage bench's measured collective exposure and no recovery lever
    # (gate C7 / O2, measured NOT MET): terms derived here from the committed campaign against this design point's
    # own on-path nodes
    import collective_exposure as CX
    import v41_collective_exposure as VX
    camp = json.loads(VX.CAMPAIGN.read_text())
    ml = m_lanes(chosen["tp"], chosen["stage"], chosen["two_step"])
    cond = conditioning_s(chosen["stage"])
    rec["draft_conditioning"] = dict(
        bytes_per_verify=conditioning_bytes(), seconds=cond, stage_lanes=chosen["stage"],
        link_Bps=2 * chosen["stage"] * LANE_NET_BPS, ucie_Bps=UCIE_BPS,
        basis="3 target layers (37-39) x hidden x BF16 x gamma + 1 positions, a head hop's bytes on the stage lanes + "
              "the UCIe half, on the MTP critical path before the draft starts (priced in every MTP rate here)")
    dump = VX.dump_on_path(U, A, sp, list(muts) + [ml], hz)
    terms, per_pattern = VX.derive_terms(camp, dump)
    xm = CX.mutation(terms)
    ab = {str(c): LX.evaluate(sp, c, muts + [ml, xm], hz=hz, draft_extra_s=cond) for c in CONTEXTS}
    rec["design_point_no_levers"] = {c: dict(ar=v["ar"], mtp=v["mtp"], T_us=v["T_us"], verify_us=v["verify_us"],
                                             breakdown_us=v["breakdown_us"]) for c, v in ab.items()}
    # the HEADLINE: the adopted collective levers (results/rtl/v41_collective_levers_campaign.json, levers 1-4 of
    # tools/v41_collective_exposure.lever_scenarios 'recommended'): their bench-measured tails, the relayed classes'
    # halved T1 bytes, and hc_post's early start.  A conditioned design-point model result, not chip throughput.
    lev_camp = json.loads(VX.LEVERS_CAMPAIGN.read_text())
    dump_mtp = VX.dump_on_path(U, A, sp, list(muts) + [ml], hz, positions=U.GAMMA + 1)
    lev = VX.recommended_exposure(dump, camp, lev_camp, dump_mtp=dump_mtp)
    lx = [CX.mutation(lev["terms"])] + ([CX.consumer_mutation(tuple(lev["consumers"]))] if lev["consumers"] else [])
    exp = {str(c): LX.evaluate(sp, c, muts + [ml] + lx, hz=hz, draft_extra_s=cond) for c in CONTEXTS}
    rec["design_point"] = {c: dict(ar=v["ar"], mtp=v["mtp"], T_us=v["T_us"], verify_us=v["verify_us"],
                                   breakdown_us=v["breakdown_us"]) for c, v in exp.items()}
    # ON-DIE WIRE (results/arch/v41_die_assembly.json floorplan): the headline carries it on the ASAP7 routed-wire
    # model; the 150 ps/mm technology entry (and its 250 ps/mm high end) are sensitivities; the same point without
    # any on-die wire is the one pre-wire ablation
    mtp_hop = lev["terms"]["hop_mtp"]
    lx_pre = [CX.mutation({k: v for k, v in lev["terms"].items() if k != "hop_mtp"})] + lx[1:]
    wsens = {}
    for wm_ in WIRE_SENSITIVITIES:
        ms_ = muts_pre_wire + [wire_mutation(wm_, sp=sp), ml] + lx
        wsens[wm_] = {str(c): {k: v for k, v in LX.evaluate(sp, c, ms_, hz=hz, draft_extra_s=cond).items()
                               if k in ("ar", "mtp", "T_us", "verify_us")} for c in CONTEXTS}
    pre = {str(c): LX.evaluate(sp, c, muts_pre_wire + [ml] + lx, hz=hz, draft_extra_s=cond) for c in CONTEXTS}
    geo = WIRE.geometry
    import v41_die_assembly as DA
    rec["on_die_wire"] = dict(
        model=WIRE_MODEL, basis=("registered traversals on the design-point DAG (wire_mutation): floorplan "
                                 "distances of tools/v41_die_assembly.traversal_geometry at the design point's "
                                 "pooled widths, cycles = ceil(distance / per-cycle reach) at the design clock; "
                                 "the DAG charges a traversal only where its node is on the critical path"),
        distances_mm=geo["distances_mm"],
        cycles={m_: DA.traversal_cycles(geo, m_, hz[0]) for m_ in geo["models"]},
        models={m_: {k: v for k, v in x.items()} for m_, x in geo["models"].items()},
        traversals=DA.TRAVERSALS,
        attribution={str(c): dict(ar=wire_attribution(sp, muts + [ml] + lx, hz, c),
                                  mtp_verify=wire_attribution(sp, muts + [ml] + lx, hz, c, U.GAMMA + 1))
                     for c in CONTEXTS},
        sensitivities=wsens,
        design_point_pre_wire={c: dict(ar=v["ar"], mtp=v["mtp"], T_us=v["T_us"], verify_us=v["verify_us"])
                               for c, v in pre.items()},
        note=("design_point is the headline WITH the wire (ASAP7 routed-wire fit, the conservative model); "
              "design_point_pre_wire is the single ablation without any on-die wire; sensitivities re-price the "
              "same traversals at technology.json's 150 ps/mm and its 250 ps/mm high end"))
    rec["mtp_hop_split"] = dict(
        lever="the MTP verify pass's stage hop at its best bench-measured T1 split (split20 kept for the "
              "one-position hop)", term=mtp_hop,
        campaign=str(VX.HOP_BATCH_CAMPAIGN.relative_to(ROOT)),
        campaign_binding_note=("not embedded: the campaign pins this record (its T1 background is derived from this "
                               "design point), so its binding is read live (tools/v41_collective_exposure."
                               "campaign_binding) and recorded in results/arch/v41_hop_batch_sensitivity.json"),
        design_point_proportional_split_extrapolated={
            str(c): LX.evaluate(sp, c, muts + [ml] + lx_pre, hz=hz, draft_extra_s=cond)["mtp"] for c in CONTEXTS},
        note=("before this lever the verify pass's hop was the one-position residual extrapolated to 6 positions "
              "(model_extrapolated_exposed_cycles per hop); the bench measures the 6-position hop at the "
              "proportional split (proportional_tail_cycles) and at its best split (measured_tail_cycles); the "
              "headline now carries the measured best"))
    dpo, dpn, dpl = rec["design_point_overlap_assumed"], rec["design_point_no_levers"], rec["design_point"]
    rec["collective_exposure"] = dict(
        gate="C7 / O2",
        status=("NOT MET (measured): the one-shot engine's exposed tails exceed the overlap model; the adopted "
                "levers recover part of the loss"),
        campaign=str(VX.CAMPAIGN.relative_to(ROOT)), campaign_binding=VX.campaign_binding(camp),
        terms=terms, per_pattern=per_pattern,
        loss_no_levers={c: dict(ar=1 - dpn[c]["ar"] / dpo[c]["ar"], mtp=1 - dpn[c]["mtp"] / dpo[c]["mtp"])
                        for c in dpn},
        levers=dict(campaign=str(VX.LEVERS_CAMPAIGN.relative_to(ROOT)),
                    campaign_binding=VX.campaign_binding(lev_camp, VX.LEVERS_CAMPAIGN),
                    scenario=lev["scenario"], why=lev["why"], tails=lev["tails"], consumers=lev["consumers"],
                    bytes_scale=lev["bytes_scale"], picks=lev["picks"], terms=lev["terms"],
                    per_pattern=lev["per_pattern"]),
        loss={c: dict(ar=1 - dpl[c]["ar"] / dpo[c]["ar"], mtp=1 - dpl[c]["mtp"] / dpo[c]["mtp"]) for c in dpl},
        recovered_share={c: dict(ar=(dpl[c]["ar"] - dpn[c]["ar"]) / (dpo[c]["ar"] - dpn[c]["ar"]),
                                 mtp=(dpl[c]["mtp"] - dpn[c]["mtp"]) / (dpo[c]["mtp"] - dpn[c]["mtp"]))
                         for c in dpl},
        note=("design_point is the headline (bench-measured tails with the adopted levers: a conditioned "
              "design-point model result, not measured chip throughput); design_point_no_levers is the ablation "
              "(measured exposure, no recovery); design_point_overlap_assumed is the conditional point that holds "
              "only if C7 is fully recovered.  With MTP the lever point can exceed the overlap-assumed one: the "
              "relay halves the bytes each T1 link carries, which the overlap-assumed point charges in full "
              "(tools/collective_exposure.py, tools/v41_collective_exposure.py)"))
    # energy with SerDes static (C4) and head-die HBM (C10), against the best comparator (its SerDes added too)
    hbrec = json.loads((ROOT / "results/arch/v41_hbm_best.json").read_text())
    rs = json.loads((ROOT / "results/arch/v41_utilization.json").read_text())["nonlayer_right_size"]
    ST = U.static_terms()
    blk, head_keep, eng_keep = (rs["engine_area_per_die_spec_mm2"], rs["head_die_keeps_mm2"],
                                rs["engram_die_keeps_mm2"])
    layer_w = ST["layer_die"]
    head_w = layer_w - ST["logic_density"] * (blk - head_keep)               # keeps its 4 stacks and SerDes (C10)
    table_w = (layer_w - ST["hbm_idle"] - ST["logic_density"] * (blk - eng_keep) - ST["serdes"]
               + ST["table_serdes"])
    rom_static = U.LAYER_DIES * layer_w + U.HEAD_DIES * head_w + (U.NONLAYER_DIES - U.HEAD_DIES) * table_w
    rom_switch_w = SWITCH * 112e9 * 2 / 1e12 * math.ceil(U.DIES / 2) * ST["switch_w_per_tbps"]
    rec["static_w"] = dict(rom_total=rom_static, layer_die=layer_w, head_die=head_w, table_die=table_w,
                           rom_serdes=(U.LAYER_DIES + U.HEAD_DIES) * ST["serdes"]
                           + (U.NONLAYER_DIES - U.HEAD_DIES) * ST["table_serdes"],
                           rom_switch_w=rom_switch_w, wall_factor=ST["wall"],
                           switch_basis=f"{ST['switch_w_per_tbps']:.1f} W per Tb/s of port capacity (NVL72: 9 x 1.5 "
                                        "kW trays, ASSUMED, over 72 GPUs x 14.4 Tb/s); the ROM rack's off-path switch "
                                        "carries 4 lanes x 112G both ways per package",
                           source=ST["source"])
    ms = muts + [ml] + lx                                 # energy and aggregates at the headline (with the levers)
    import v41_rack_design as RK
    dem = RK.stage_link_demand(RK.placement(), rack_levers(lev), RK.residual_bytes())
    rec["link_demand"] = dict(busiest_t1_stage=dem["busiest_t1_stage"], busiest_ucie_stage=dem["busiest_ucie_stage"],
                              busiest_stage_bytes_per_position=dem["per_stage"][dem["busiest_t1_stage"]],
                              busiest_ucie_stage_bytes_per_position=dem["per_stage"][dem["busiest_ucie_stage"]],
                              head_module=dem["head_module"],
                              source="tools/v41_rack_design.stage_link_demand (the C8 gate's accounting)")
    energy = {}
    for ctx in CONTEXTS:
        rows = {}
        top = hbrec["rungs"]["top"]["energy"][str(ctx)]
        for ptag, bt in HB.POINTS:
            for mtp in (False, True):
                k = ptag + ("_mtp" if mtp else "")
                bt_ = A.point_batch(ptag, bt, ctx)              # a saturated point holds at most the users held
                with LX.clock(hz[0]), U.params(**hz[1]):
                    r_ = U.op_point(sp, ctx, bt_, mtp=mtp, levers=U.CHAIN_L3, muts=ms, units=U.POOLED_UNITS,
                                    draft_extra_s=cond if mtp else 0.0, contention=True)
                r_["cycle_s"] = r_["period_us"] * 1e-6
                # the busiest package link caps the aggregate (the period stretches to keep it at 100%)
                lk = link_cap(r_, dem, chosen, mtp)
                lk["aggregate_tokens_s_uncapped"] = r_["aggregate_tokens_s"]
                if lk["cap"] < 1.0:
                    r_["aggregate_tokens_s"] *= lk["cap"]
                    r_["tokens_s_per_user"] *= lk["cap"]
                    r_["cycle_s"] /= lk["cap"]
                lk["utilisation"] = {kk: vv * lk["cap"] for kk, vv in lk["utilisation_uncapped"].items()}
                if r_.get("draft_contention"):
                    # contention is solved at the uncapped rate: an upper bound on the head load once the link caps it
                    r_["draft_contention"]["evaluated_at"] = ("the uncapped aggregate (the link cap applies after: an "
                                                              "upper bound on the head load)" if lk["cap"] < 1.0
                                                              else "the point's aggregate")
                e_rom = HB.energy_point(sp, ctx, r_, U.LAYER_DIES, 28, LX.area(sp, U.MTP_M if mtp else 1),
                                        rom_static)
                h = top[k]["hbm"]                            # board-mesh comparator (its static already inside)
                h_total, h_static = h["total_j"], h["static_j"]
                rows[k] = dict(batch=bt_, users_held=A.users_held(ctx), hbm_batch=h.get("batch"),
                               stage_busy_us=r_["stage_busy_us"], pass_T_us=r_["pass_T_us"],
                               rom=dict(tokens_s_per_user=r_["tokens_s_per_user"],
                                        aggregate_tokens_s=r_["aggregate_tokens_s"], **e_rom),
                               link_cap=lk, draft_contention=r_.get("draft_contention"),
                               draft_conditioning_us=r_["draft_extra_us"],
                               hbm=dict(G=h["G"], m=h["m"], tokens_s_per_user=h["tokens_s_per_user"],
                                        aggregate_tokens_s=h["aggregate_tokens_s"], dynamic_j=h["dynamic_j"],
                                        static_j=h_static, total_j=h_total),
                               ratio_rate_per_user=r_["tokens_s_per_user"] / h["tokens_s_per_user"],
                               ratio_energy_with_static=h_total / e_rom["total_j"],
                               ratio_energy_dynamic=h["dynamic_j"] / e_rom["dynamic_j"])
        energy[str(ctx)] = rows
    rec["energy"] = energy
    rec["note"] = ("the HBM rows here are the BOARD-MESH comparator (results/arch/v41_hbm_best.json), kept for "
                   "reference; the headline comparator is the switched NVL72 domain (tools/arch_hbm_switched_v41.py), "
                   "which also applies the switch power and the wall chain to both machines")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: None) + "\n")
    print("ladder top, no lane pricing:", {c: (round(v["ar"]), round(v["mtp"])) for c, v in rec["ladder_top_overlap_assumed"].items()})
    print("design point, overlap assumed (conditional):", {c: (round(v["ar"]), round(v["mtp"])) for c, v in rec["design_point_overlap_assumed"].items()})
    print("design point, measured C7 exposure without levers (ablation):", {c: (round(v["ar"]), round(v["mtp"])) for c, v in rec["design_point_no_levers"].items()})
    print("design point, bench tails with the adopted levers (headline):", {c: (round(v["ar"]), round(v["mtp"])) for c, v in rec["design_point"].items()})
    for r in rec["grid"]:
        print(r["tp"], r["stage"], r["spare"], r["two_step"], {c: (round(r[c]["ar"]), round(r[c]["mtp"]), round(r[c]["collective_bytes_us"], 2),
                                                    round(r[c]["hops_us"], 2)) for c in ("1048576", "200000")})
    print("best", rec["best_split"]["tp"], rec["best_split"]["stage"], rec["best_split"]["two_step"], "adopted",
          rec["best_adopted"])
    print("static", {k: round(v) for k, v in rec["static_w"].items() if isinstance(v, (int, float))})
    for c, rows in rec["energy"].items():
        for k, v in rows.items():
            print(c, k, f"rom {v['rom']['total_j'] * 1e3:.1f} hbm {v['hbm']['total_j'] * 1e3:.1f} "
                        f"x{v['ratio_energy_with_static']:.2f} rate x{v['ratio_rate_per_user']:.2f}")


if __name__ == "__main__":
    main()
