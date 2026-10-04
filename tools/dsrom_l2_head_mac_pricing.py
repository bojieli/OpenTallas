#!/usr/bin/env python3
"""Price the physical cost of DS ROM lever L2 (the batched DSpark draft head) on the S81 head dies.

L2 runs the lm_head matvec of all k draft-slot vectors in ONE head ROM sweep.  The S81 head is BF16 on the standard
pair (BP = 2: a 16-weight word held 8 cycles against 2 multipliers per macro), so the head is MAC-bound per pair and a
k-vector sweep keeps the single-vector sweep time only if each pair carries k copies of its BF16 datapath
(rtl/v41rom/ot_v41_rom_elem_nv_w10.sv, NV = k: per macro per extra vector 2 multipliers, 2 chunk chains, the pair
adder, a segment tree, an x FIFO; per element an NV-way partial arbiter).

Measured input (results/physical_abi3/asap7/chip/dsrom_l2_head_20261004/screen.json): ORFS synthesis cell area of
the whole pair element at NV = 1..6 and its SS pre-layout timing (tools/gpu_ss_prelayout.py + the macro's SS liberty).
Model (this file): per-die area = lm_head pairs per head die x the measured cell-area delta / the S81 logic
reservation density (0.5, the S81 ledger's cell-only 50% reservation), against the head die's own content priced on
the S81 layer-die debits.  Per-user rates are the L1 + L2 composition's (results/rtl/dsrom_dspark_l1l2_20261004,
ROM-read bound, which is exactly what NV copies buy).

    python3 tools/dsrom_l2_head_mac_pricing.py [--out results/uarch/dsrom_l2_head_mac_20261004/model.json]
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "results/physical_abi3/asap7/chip/dsrom_l2_head_20261004/screen.json"
INV = ROOT / "results/uarch/dsrom_s81_unified_components_20261004/inputs/inventory.json"
DEC = ROOT / "results/uarch/dsrom_c_recheck_20261004/model.json"
COMPOSE = ROOT / "results/rtl/dsrom_dspark_l1l2_20261004/expected.json"
DSPARK = ROOT / "results/speculative/v41_flash_dspark_feasibility.json"
OUT = ROOT / "results/uarch/dsrom_l2_head_mac_20261004/model.json"
NVS = (1, 2, 3, 5, 6)
DENSITY = 0.5                    # S81 ledger: cell-only 50% reservation for added logic
PAIR_BYTES = 4 * 4096 * 256 // 8  # 4 ROM4096 macros x 256 data bits a word (inventory word_data_bits)
HEAD_GROUPS = (8, 12)            # head dies: the S81 8, and one more TP-4 group


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    scr, inv, dec = (json.loads(p.read_text()) for p in (SCREEN, INV, DEC))
    comp = json.loads(COMPOSE.read_text())["result"]
    ds_bytes = json.loads(DSPARK.read_text())["inventory"]["mtp"]["bytes"]
    s81 = dec["priced"]["S81_ragged_RD64_replicated"]["area"]
    pair_mm2 = s81["variable"] / s81["pairs"]                      # S81 ROM field per pair
    non_field = s81["die_mm2"] - s81["variable"]                    # fixed + increments + return, per die
    reticle, target = dec["reticle_mm2"], dec["margin_target_die_mm2"]
    g = {t["tensor"]: t for t in inv["dedicated_storage"]["global_tensors"]}
    head_pairs = g["head.weight"]["pairs"]
    global_pairs = sum(t["pairs"] for t in g.values())
    dspark_pairs = math.ceil(ds_bytes / PAIR_BYTES)
    runs = scr["runs"]
    el = {nv: runs[f"ot_v41_rom_elem_nv_w10_nv{nv}"] for nv in NVS}
    base = el[1]["cell_area_um2"]
    l1 = comp["reference"]["l1"]["ctx"]
    variants = []
    for nv in NVS:
        d_cell = el[nv]["cell_area_um2"] - base
        row = dict(NV=nv, pair_cell_um2=round(el[nv]["cell_area_um2"], 1), pair_delta_cell_um2=round(d_cell, 1),
                   pair_delta_per_extra_vector_um2=round(d_cell / (nv - 1), 1) if nv > 1 else 0.0,
                   pair_delta_placed_um2=round(d_cell / DENSITY, 1),
                   ss_prelayout_wns_ps=el[nv]["ss_setup_wns_ps"], ss_worst_end=el[nv]["worst_end"], head_groups={})
        for H in HEAD_GROUPS:
            lm_pd = head_pairs / H
            content = (global_pairs + dspark_pairs) / H
            die0 = non_field + content * pair_mm2
            d_die = lm_pd * d_cell / DENSITY * 1e-6
            die = die0 + d_die
            row["head_groups"][H] = dict(lm_head_pairs_per_die=round(lm_pd, 1), content_pairs_per_die=round(content, 1),
                                         head_die_before_L2_mm2=round(die0, 2), L2_delta_per_die_mm2=round(d_die, 2),
                                         head_die_mm2=round(die, 2), margin_to_reticle_mm2=round(reticle - die, 2),
                                         fits_reticle=die <= reticle, meets_2pct_target=die <= target,
                                         total_dies=s81_total(dec) - 8 + H)
        if nv > 1:
            k = f"l1l2/rom_read/k{nv}"
            r = comp["levers"][k]["ctx"]
            row["mtp_tok_s_1M_occupancy"] = r["1048576"]["occupancy"]["mtp_tok_s"]
            row["gain_over_L1_1M"] = round(r["1048576"]["occupancy"]["mtp_tok_s"] / l1["1048576"]["occupancy"]["mtp_tok_s"] - 1, 4)
            row["gain_over_L1_200K"] = round(r["200000"]["occupancy"]["mtp_tok_s"] / l1["200000"]["occupancy"]["mtp_tok_s"] - 1, 4)
            vs = comp["levers"][k].get("verify_head_batched_sensitivity")
            if vs:
                row["verify6_batched_mtp_tok_s_1M"] = vs["1048576"]["occupancy"]["mtp_tok_s"]
        variants.append(row)
    v = {r["NV"]: r for r in variants}
    noise = [runs[k]["ss_setup_wns_ps"] for k in ("ot_v41_rom_elem_w10_nv1", "ot_v41_rom_elem_nv_w10_nv1", "d994_nv1")
             if k in runs]
    verdict = dict(
        recommended_NV=5,
        recommended_head_dies=12,
        area=(f"H = 8 (S81): the head die is {v[1]['head_groups'][8]['head_die_mm2']} mm2 BEFORE L2; no NV > 1 fits the "
              f"{reticle:g} mm2 reticle (NV2 {v[2]['head_groups'][8]['head_die_mm2']}, NV5 {v[5]['head_groups'][8]['head_die_mm2']}). "
              f"H = 12 (+4 dies, {v[5]['head_groups'][12]['total_dies']} total): NV5 {v[5]['head_groups'][12]['head_die_mm2']} mm2, "
              f"NV6 {v[6]['head_groups'][12]['head_die_mm2']} mm2, both under the 2% target."),
        rate=(f"L1+L2 over L1 at 1M: NV2 {v[2]['gain_over_L1_1M']:+.2%}, NV3 {v[3]['gain_over_L1_1M']:+.2%}, "
              f"NV5 {v[5]['gain_over_L1_1M']:+.2%}, NV6 {v[6]['gain_over_L1_1M']:+.2%}; NV6's extra (6 verify heads batched) "
              f"{v[6]['verify6_batched_mtp_tok_s_1M'] / v[6]['mtp_tok_s_1M_occupancy'] - 1:+.2%} < 1%: REJECT NV6."),
        timing=(f"SS pre-layout at 833 ps: NV1 {min(noise)}..{max(noise)} ps (ABC run-to-run, same logic); NV2 "
                f"{v[2]['ss_prelayout_wns_ps']}, NV3 {v[3]['ss_prelayout_wns_ps']}, NV5 {v[5]['ss_prelayout_wns_ps']}, NV6 "
                f"{v[6]['ss_prelayout_wns_ps']} ps.  NV-only paths: capture-round bound bn_lim = bn_tot x (plast + 1) "
                "feeding b_lo/b_hi and bn_pos; the NV-way partial arbiter (o_v/o_row/o_seg, fb_cnt) at NV >= 5; the shared "
                "word/x hold registers fanning out to 2 x NV multipliers (s2_p).  Screen FAILS relative to NV1: no route "
                "until the RTL registers bn_lim, pipelines the arbiter and duplicates the hold registers per copy."),
    )
    out = dict(
        schema="opentallas.uarch.dsrom_l2_head_mac.v1",
        verdict=verdict,
        question="Physical feasibility of L2 (batched DSpark draft head) on the S81 head dies",
        basis=dict(head_dies_S81=inv["head_dies"], lm_head_pairs_total=head_pairs, global_pairs=global_pairs,
                   dspark_pairs=dspark_pairs, dspark_bytes=ds_bytes, pair_bytes=PAIR_BYTES,
                   S81_pair_field_mm2=round(pair_mm2, 6), S81_non_field_debit_mm2=round(non_field, 3),
                   S81_layer_die_mm2=s81["die_mm2"], S81_layer_pairs=s81["pairs"], reticle_mm2=reticle,
                   margin_target_mm2=target, logic_density=DENSITY,
                   head_element="ot_v41_rom_elem_nv_w10 FAST PP BP=2 MTP NB=2 EARLY (the pair: 2 logical macros = 4 ROM4096)",
                   head_rate="BP=2: 2 BF16 MACs/cycle/macro = 4 per pair; a word read once per 8 cycles (MAC-bound)",
                   notes=["The head die is priced on the S81 layer die's non-field debits (fixed + increments + return): "
                          "the head die repeats the layer floorplan; its own ledger is not qualified "
                          "(inventory head_compute_shape_and_rowtree_binding_qualified = False).",
                          "Head-die content = embed + head + norm (inventory globals) + the DSpark drafter (mtp.0-2, "
                          "7.93 GB) at 256 data bits a word; the S81 inventory lists only the globals (632 pairs a die)."]),
        screen=dict(record=str(SCREEN.relative_to(ROOT)), sha256=sha(SCREEN)),
        variants=variants,
        inputs_sha256={str(p.relative_to(ROOT)): sha(p) for p in (SCREEN, INV, DEC, COMPOSE, DSPARK)},
        tool_sha256=sha(__file__))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for r in variants:
        h8, h12 = r["head_groups"][8], r["head_groups"][12]
        print(f"NV{r['NV']}: +{r['pair_delta_cell_um2']:>8.0f} um2/pair  WNS {r['ss_prelayout_wns_ps']:>7}  "
              f"H8 {h8['head_die_mm2']:.1f} mm2 ({h8['margin_to_reticle_mm2']:+.1f})  "
              f"H12 {h12['head_die_mm2']:.1f} mm2 ({h12['margin_to_reticle_mm2']:+.1f})  "
              f"gain/L1 1M {r.get('gain_over_L1_1M')}")


def s81_total(dec):
    return dec["priced"]["S81_ragged_RD64_replicated"]["system"]["total_dies"]


if __name__ == "__main__":
    main()
