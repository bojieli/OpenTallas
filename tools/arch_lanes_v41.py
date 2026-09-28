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
C4  SerDes static power: 84 always-on lanes per layer/head package at ~0.56 W each (~5 pJ/bit at 112 Gb/s) = 47 W per
    package, 23.5 W per die; the 72 Engram table dies carry ~1 lane-pair each (0.56 W per die).  The HBM comparator's
    NVLink-class SerDes is charged the same way: 84 always-on 112G lanes per 2-die package at the same pJ/bit
    (ASSUMED: its packages have the same edge and lane count), 23.5 W per die.
C10 The 4 head dies carry 4 HBM3E stacks each for the drafter's per-user state (+16 x 2.8 W).
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
UCIE_BPS = 4.2e12
LANE_W = 112e9 * 6.5e-12                           # 112 Gb/s x 6.5 pJ/b (technology.json energy.link_j_per_bit)
ACTIVE_LANES_PKG = 84
SERDES_W_DIE = ACTIVE_LANES_PKG * LANE_W / 2       # 23.52 W
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


def design_point(split=None):
    """The adopted design point: the ladder's top with the chosen lane split (this tool's record, best_split if
    adopted else the rack's).  Returns sp, muts (without the lane pricing), hz, the split and its lane mutation."""
    sp, muts, hz = _ladder_top()
    if split is None:
        rec = json.loads(OUT.read_text())
        split = rec["best_split"] if rec["best_adopted"] else rec["rack_split_result"]
    split = dict(tp=split["tp"], stage=split["stage"], two_step=split["two_step"])
    return dict(sp=sp, muts=list(muts), hz=hz, split=split, ml=m_lanes(split["tp"], split["stage"], split["two_step"]))


def build():
    E = A._env()
    sp, muts, hz = _ladder_top()
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
            r = LX.evaluate(sp, ctx, muts + [m_lanes(s["tp"], s["stage"], ts)], hz=hz)
            row[str(ctx)] = dict(ar=r["ar"], mtp=r["mtp"], T_us=r["T_us"], verify_us=r["verify_us"],
                                 collective_bytes_us=r["breakdown_us"]["collective_bytes"],
                                 hops_us=r["breakdown_us"]["pipeline_hops"])
        grid.append(row)
    rec["grid"] = grid
    rack = next(r for r in grid if r["tp"] == RACK_SPLIT["tp"] and not r["two_step"])
    # the best split: highest 1M rate with MTP, then without; it must not be slower than the rack's anywhere
    key = lambda r: (math.sqrt(r["1048576"]["mtp"] * r["1048576"]["ar"]))  # noqa: E731
    best = max(grid, key=key)
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
    dump = VX.dump_on_path(U, A, sp, list(muts) + [ml], hz)
    terms, per_pattern = VX.derive_terms(camp, dump)
    xm = CX.mutation(terms)
    ab = {str(c): LX.evaluate(sp, c, muts + [ml, xm], hz=hz) for c in CONTEXTS}
    rec["design_point_no_levers"] = {c: dict(ar=v["ar"], mtp=v["mtp"], T_us=v["T_us"], verify_us=v["verify_us"],
                                             breakdown_us=v["breakdown_us"]) for c, v in ab.items()}
    # the HEADLINE: the adopted collective levers (results/rtl/v41_collective_levers_campaign.json, levers 1-4 of
    # tools/v41_collective_exposure.lever_scenarios 'recommended'): their bench-measured tails, the relayed classes'
    # halved T1 bytes, and hc_post's early start.  A conditioned design-point model result, not chip throughput.
    lev_camp = json.loads(VX.LEVERS_CAMPAIGN.read_text())
    lev = VX.recommended_exposure(dump, camp, lev_camp)
    lx = [CX.mutation(lev["terms"])] + ([CX.consumer_mutation(tuple(lev["consumers"]))] if lev["consumers"] else [])
    exp = {str(c): LX.evaluate(sp, c, muts + [ml] + lx, hz=hz) for c in CONTEXTS}
    rec["design_point"] = {c: dict(ar=v["ar"], mtp=v["mtp"], T_us=v["T_us"], verify_us=v["verify_us"],
                                   breakdown_us=v["breakdown_us"]) for c, v in exp.items()}
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
    energy = {}
    for ctx in CONTEXTS:
        rows = {}
        top = hbrec["rungs"]["top"]["energy"][str(ctx)]
        for ptag, bt in HB.POINTS:
            for mtp in (False, True):
                k = ptag + ("_mtp" if mtp else "")
                with LX.clock(hz[0]), U.params(**hz[1]):
                    r_ = U.op_point(sp, ctx, bt, mtp=mtp, levers=U.CHAIN_L3, muts=ms, units=U.POOLED_UNITS)
                r_["cycle_s"] = r_["period_us"] * 1e-6
                e_rom = HB.energy_point(sp, ctx, r_, U.LAYER_DIES, 28, LX.area(sp, U.MTP_M if mtp else 1),
                                        rom_static)
                h = top[k]["hbm"]                            # board-mesh comparator (its static already inside)
                h_total, h_static = h["total_j"], h["static_j"]
                rows[k] = dict(rom=dict(tokens_s_per_user=r_["tokens_s_per_user"],
                                        aggregate_tokens_s=r_["aggregate_tokens_s"], **e_rom),
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
