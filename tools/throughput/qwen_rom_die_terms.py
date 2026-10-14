#!/usr/bin/env python3
"""Qwen ROM per-layer record, part 2: the DIE-LEVEL terms of the priced production layer that the s22ml7 per-layer
vehicle (results/rtl/qwen_layer_tput_1013/record.json: 5,480 of the 6,835-cycle layer) does not hold, measured on the
SAME vehicle (tools/qwen_missing/partition_token.py, TP4, L0-L2 chained at P 8,191, exact against the golden) by
building it at the priced station / stage counts:

  issue relays (623)   the r22k sequencer <-> tree-top / SU issue and status relays as unit pin stations:
                       --dcu 7 --duc 7 --dcu-me 37 --duc-me 37 --su-ml 10 (results/arch/qwen_kv_die_20261009/split_relays.json)
  die relays (432)     the r21 relay stations as the die's wire-stage counts: QROM_BD 77, QROM_TWS 93, QROM_ORD 10 and the
                       package link QROM_LAT 339 + 26 (results/rtl/qwen_rom_die_r17_20261005/relays_r21/relay_token_cost.json;
                       the tree's 20 -> 21 is one stage in four levels of NWS and cannot be set: 4 cycles a layer stay priced)
  KV attention swap    the attention on the KV die through the link (1,816 priced against the 1,550 of the tile attention):
                       the KV-die head group bench HEAD_HS_TPUT, its own vehicle

    qwen_rom_die_terms.py --runs DIR --out results/rtl/qwen_layer_tput_1013/die_terms.json
DIR/<name>/result.json for name in qA_r22k_ml10, qB_dierelay, qC_all_ml10, qD_all_ml15, qE_all_ml10_mut and, round 5,
qF_all_ml15_x16 / qG_all_ml15_x14 (qD + the VM x read at +16 / +14 edges: QROM_XVM 17 / 15 with QROM_BD 93 / 91, the
whole TP4-vehicle composition in ONE run) and qH_all_ml15_x16_mut (qF with --comp 0 on L0, must fail).
Track B (one die type, KV merged): the attention term is the merged-die sequencer layer step (1,794 cycles, bench
physical/qwen_kv_centre/seq_layer_bench.sh), not the two-die head group bench (1,847).
Nothing is re-priced: every figure is measured / the committed price.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "throughput"))
import accepted_cost as AC  # noqa: E402

REC = ROOT / "results/rtl/qwen_layer_tput_1013/record.json"
# the merged-die KV sequencer layer step, cluster == flat, 14 / 14 exact, 5 mutants fail (closure-loop bench of the
# qkd_seq cluster leaves at dbf8a21da; span = launch descriptor sent -> last RES word at the VM face, context 8,192:
# the span of the priced 1,816 and of the two-die gate's 1,842)
KV_SEQ = ROOT / "results/closure_loop/runner_fixes_1013_pm/qkd_seq_layer_count/qkd_seq_core-kc2-dbf8a21da.original_exact.log"
KV_PRICE, KV_TWO_DIE, TILE_ATTN = 1816, 1842, 1550
QUAL = 1.10
ME_OPS, LINKS = 4, 2                      # ME ops and all-reduces a layer
R21 = dict(bd=(41, 77), tree=(20, 21), tws=(38, 93), ord=(7, 10), link=(46, 72))


def J(p):
    return json.loads(Path(p).read_text())


def token(delta_layer, delta_l0=None, head=0.0):
    """added cycles a layer on the 36 layers (L0 its own figure) + the head -> tok/s loss on the committed token path"""
    doc = J(AC.TP / "qwen_rom.json")
    base, _ = AC.solve(doc["nodes"], doc["edges"])
    d = {}
    for n in doc["nodes"]:
        if n["id"].endswith(".allreduce2"):
            d[n["id"]] = delta_l0 if (delta_l0 is not None and n["id"].startswith("L0.")) else delta_layer
        if n["id"] == "head.lm_head":
            d[n["id"]] = head
    new, _ = AC.solve(doc["nodes"], doc["edges"], d)
    return dict(base_cycles=base, added_cycles=round(new - base, 1), e2e_loss_pct=round(AC.loss_pct(base, new), 3))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sha", default="")
    a = ap.parse_args()
    rec = J(REC)
    base = rec["exact"]["positive"]["stage_cycles"]                 # s22ml7: L0 6151 / L1 5480 / L2 5480
    pm = rec["layer"]["price"]["production_minus_vehicle"]
    P_ISSUE, P_DIE, P_KV = pm["issue_relays_r22k"], pm["die_relays_430um"], pm["kv_die_attention_swap"]
    per_me = sum(b - a_ for k, (a_, b) in R21.items() if k != "link")          # 95
    in_vehicle = ME_OPS * (per_me - (R21["tree"][1] - R21["tree"][0])) + LINKS * (R21["link"][1] - R21["link"][0])   # 428

    runs = {}
    for name in ("qA_r22k_ml10", "qB_dierelay", "qC_all_ml10", "qD_all_ml15", "qE_all_ml10_mut",
                 "qF_all_ml15_x16", "qG_all_ml15_x14", "qH_all_ml15_x16_mut"):
        p = a.runs / name / "result.json"
        if p.exists():
            r = J(p)
            runs[name] = dict(exact=r["exact"], stage_cycles=r["stage_cycles"], layer_x=f"{r['layer_x_mismatches']}/{r['layer_x_checks']}",
                              kv=f"{r['kv_mismatches']}/{r['kv_checks']}", executable_sha256=r.get("executable_sha256"),
                              env=(a.runs / name / "env").read_text().split() if (a.runs / name / "env").exists() else [])

    def L1(n):
        return runs[n]["stage_cycles"]["L1"] if n in runs and "L1" in runs[n]["stage_cycles"] else None

    def row(name, what, priced_delta, params):
        m = L1(name)
        if m is None:
            return dict(run=name, what=what, status="NOT RUN")
        d = m - base["L1"]
        return dict(run=name, what=what, params=params, exact=runs[name]["exact"], measured_layer=m,
                    priced_layer=base["L1"] + priced_delta, ratio=round(m / (base["L1"] + priced_delta), 4),
                    measured_delta=d, priced_delta=priced_delta,
                    delta_ratio=round(d / priced_delta, 3) if priced_delta else None,
                    l0=dict(measured=runs[name]["stage_cycles"]["L0"], delta=runs[name]["stage_cycles"]["L0"] - base["L0"]),
                    qualified=bool(runs[name]["exact"] and m / (base["L1"] + priced_delta) <= QUAL))

    terms = dict(
        issue_relays=row("qA_r22k_ml10", "r22k issue / status relays as unit stations (the price's own configuration, rerun on current main)",
                         P_ISSUE, "--dcu 7 --duc 7 --dcu-me 37 --duc-me 37 --su-ml 10"),
        die_relays=row("qB_dierelay", "r21 die relay stations as wire-stage counts on the s22ml7 vehicle", in_vehicle,
                       "QROM_BD=77 QROM_TWS=93 QROM_ORD=10 QROM_LAT=365, --dcu 2 --duc 2 --su-ml 7"),
        issue_plus_die=row("qC_all_ml10", "both: the TP4 die composition at its priced station and stage counts", P_ISSUE + in_vehicle,
                           "qA + qB parameters"),
        issue_plus_die_su_ml15=row("qD_all_ml15", "as qC with the SU lane memory latency at the production ML 15 (priced: ML 10)",
                                   P_ISSUE + in_vehicle, "qC with --su-ml 15"))
    mut = runs.get("qE_all_ml10_mut")
    mutant = dict(what="qC built with --comp 0 (stations without the split-exact compensation), L0", status="NOT RUN") if not mut else dict(
        what="qC built with --comp 0 (stations without the split-exact compensation), L0", exact=mut["exact"], layer_x=mut["layer_x"],
        kv=mut["kv"], fails_as_required=not mut["exact"])
    kv_swap = dict(priced_delta=P_KV, vehicle="KV-die head group bench (tools/qwen_kv_die/bench_gate.sh pos + head_hs_tput_gate.py), "
                   "production 8,192-key attention, 14/14 exact, mutant fails", measured=1847, price=1816, ratio=round(1847 / 1816, 4),
                   source="el1013-qwen-kvleaves.log line 32 (loop bench on q13b: HEAD_HS_TPUT PASS 1847 / 1816); committed class record "
                          "results/rtl/tput_map_1011/qwen_kv_die/record.json = 1.0099",
                   kv_end="relayed by the coordinator: KV-end production gate 1,842 cycles against the 1,997 limit (1.10 x 1,816) = 1.014 of "
                          "the price; the figure is not in a stream log this stream could find: grade 'relayed'")

    # track B: the merged-die sequencer step, read from the committed bench log
    seq = None
    if KV_SEQ.exists():
        import re
        m = re.search(r"PASS qkd_seq_layer (\w+) runs=(\d+) exact=(\d+) step_8192=(\d+)", KV_SEQ.read_text())
        if m:
            seq = dict(measured=int(m.group(4)), price=KV_PRICE, ratio=round(int(m.group(4)) / KV_PRICE, 4), two_die=KV_TWO_DIE,
                       dut=m.group(1), runs=int(m.group(2)), exact=int(m.group(3)), evidence=str(KV_SEQ.relative_to(ROOT)),
                       qualified=bool(int(m.group(2)) == int(m.group(3)) and int(m.group(4)) / KV_PRICE <= QUAL),
                       note="merged-die KV sequencer (track B, no D2D adapters, no link 7): same span and KV-side stage counts "
                            "(ROM_ST 28, QX 29, RX 28, KVL 34) as the two-die gate; under its price, no accepted-cost row")
    kv_swap["merged_sequencer"] = seq or dict(status="NOT FOUND")

    # composed production layer at TP4: measured die composition + the attention swap at its measured KV-die figure
    comp = None
    qc = L1("qC_all_ml10")
    if qc is not None:
        other = pm["slab_mul_lat7"] + pm["band_integrate (re-price 10-08)"] + pm["serdes_pinreg (re-price 10-08)"] + ME_OPS * 1
        tile_attn_priced = 1816 - P_KV
        composed = qc + (1847 - tile_attn_priced) + other
        prod = rec["layer"]["price"]["production_layer"]
        comp = dict(measured_die_composition=qc, kv_attention_swap_measured=1847 - tile_attn_priced, still_priced=other,
                    still_priced_items="slab MUL_LAT 7 (4), band integration (28), SerDes pin register (2), tree stage 20 -> 21 (4)",
                    composed_layer=composed, priced_production_layer=prod, ratio=round(composed / prod, 4),
                    measured_fraction=round((prod - other) / prod, 4),
                    token=token(composed - prod))
        qd = L1("qD_all_ml15")
        if qd is not None:
            comp["su_ml15"] = dict(layer_delta=qd - qc, l0_delta=runs["qD_all_ml15"]["stage_cycles"]["L0"] - runs["qC_all_ml10"]["stage_cycles"]["L0"],
                                   composed_layer=composed + qd - qc, ratio=round((composed + qd - qc) / prod, 4),
                                   token=token(composed + qd - qc - prod))

    # round 5: track B composition (merged sequencer) and the one-run measurement of every vehicle-settable term
    if comp is not None and seq is not None:
        prod = rec["layer"]["price"]["production_layer"]
        kvm = seq["measured"] - TILE_ATTN

        def one(layer, l0=None):
            c = layer + kvm + comp["still_priced"]
            return dict(composed_layer=c, ratio=round(c / prod, 4), qualified=bool(c / prod <= QUAL),
                        token=token(c - prod, None if l0 is None else l0 + kvm + comp["still_priced"] - (rec["layer"]["all_layers"]["L0"]["priced"] + prod - base["L1"])))
        tb = dict(kv_attention_swap_measured=kvm, kv_attention_swap_priced=P_KV, issue_plus_die=one(L1("qC_all_ml10")))
        if L1("qD_all_ml15") is not None:
            tb["issue_plus_die_su_ml15"] = one(L1("qD_all_ml15"))
        for name, key, edges in (("qF_all_ml15_x16", "all_terms_vm_x16", 16), ("qG_all_ml15_x14", "all_terms_vm_x14", 14)):
            if L1(name) is not None:
                r = runs[name]
                tb[key] = dict(run=name, exact=r["exact"], layer_x=r["layer_x"], kv=r["kv"], stage_cycles=r["stage_cycles"],
                               what=f"issue relays + die relays + SU ML 15 + VM x read +{edges} edges in ONE exact run of the TP4 vehicle",
                               vm_x_read_delta=dict(L1=L1(name) - L1("qD_all_ml15"), L0=r["stage_cycles"]["L0"] - runs["qD_all_ml15"]["stage_cycles"]["L0"],
                                                    alone_on_s22ml7=dict(L1=6 * edges, L0=5 * edges)) if L1("qD_all_ml15") is not None else None,
                               **one(L1(name), r["stage_cycles"]["L0"]))
        mh = runs.get("qH_all_ml15_x16_mut")
        if mh:
            tb["all_terms_mutant"] = dict(what="qF built with --comp 0, L0", exact=mh["exact"], layer_x=mh["layer_x"], fails_as_required=not mh["exact"])
        comp["track_b_merged_kv"] = tb

    hand = dict(
        vm_x_read=dict(unit="VM.XREAD (TP8 bit-plane VM x transport)", x_read_edges="XPR + XQR + 3 - RO (XPR 10 / XQR 2: +14 at RO 1; plan XPR >= 12: +16)",
                       measured={"+10": dict(layers=[6201, 5540, 5540], delta=[50, 60, 60], composed_loss_pct=0.859, record="xvm11_bd51/record.json"),
                                 "+14": dict(layers=[6221, 5564, 5564], delta=[70, 84, 84], composed_loss_pct=1.198, record="xvm15_bd55/record.json"),
                                 "+16": dict(layers=[6231, 5576, 5576], delta=[80, 96, 96], composed_loss_pct=1.367, record="xvm17_bd57/record.json")},
                       per_edge="6 cycles a layer per x-read edge (5 on L0); mutants fail (16,384 X mismatches)",
                       ledger="PROPOSED at +16 (1.367 %); final when the VM stream posts the placed XPR / XQR (asked in el1013-qwen-vm.log)",
                       coordinator="acceptable (<= 5 %), 10-13 12:25"),
        su_lane_ml15=dict(bench="tb_qfd_su_vm_bv, 120 random SU ops, go -> idle edges per op (branch claude/el1013-qwen-stalls-su)",
                          priced_value="149.85 edges per op = the ML 7 lane-tile master on the flat banks at SW 8 (source 20e0883d6, exact PASS): the "
                                       "per-layer vehicle and the price run --su-ml 7 (stations) / ML 10 (r22k).  The 94.07 printed as 'ref' is "
                                       "the bare ISA unit (ot_hdc_vstream ML 0, one-edge behavioural memory), NOT a price",
                          measured={"ML15 flat tile SW 8": 157.85, "ML15 4-leaf split SW 8": 160.04, "ML15 flat tile SW 64": 158.99},
                          ratio={"ML15 flat / ML7": 1.053, "ML15 split / ML7": 1.068},
                          open="no SW 64 run of the PRICED ML 7 unit exists (158.99 has no like-for-like price); the layer effect is "
                               "terms.issue_plus_die_su_ml15 (--su-ml 15 on the per-layer vehicle, main's lane, not the 4-leaf split)"),
        die_relay_stages=dict(status="INTERIM (qwen-tp8/die r6 07:55, run v2 of the reach-gated relay plan; r9 12:30: 9,548 relays, 1 chain unrepaired)",
                              per_bus="ME op path words unchanged except rk_0..2 (result words) +2..+14 stages (rk_2 22 -> 36); KV-centre <-> strip "
                                      "words -10..-23 stages (ap_WN 99 -> 86, af_WS 98 -> 75), emf_WN +12; gq / gr 23 -> 1; krs / krq 13-18; wcf +1",
                              per_token="not posted: relay_token_cost() needs the regenerated TP8 case; the priced figure stays die_relays_430um "
                                        "(r21, TP4 die), measured here as terms.die_relays",
                              reset_tree="0 cycles per token (power-on only)"),
        die_tile_cycles=dict(status="UNMEASURED: no simulation composes the hardened qfd_* tiles; this record measures the cycle-reference "
                                    "core at the die's station / stage counts"),
        head=dict(measured=rec["head"]["measured"], price=rec["head"]["price_base"], ratio=rec["head"]["ratio"],
                  note="LM head on the stationed core (record.json)"))

    tp8 = dict(
        exists=False,
        needs=["a TP8 golden: weights partitioned over 8 ranks (gold/tp8_hs: x preload, layer X, kv_at_P per rank) from "
               "tools/qwen_hbmacc_position_oracle_gpu.py at TP 8, and the 8-rank ROM images (tile fixtures at 768 / 512 / 768 rows a die)",
               "an 8-die build of the stream4 die top (harness D = 8, all-reduce over 8 ranks: ot_rom_oneshot_allreduce N 8 or the native "
               "qfd_io_collective port) and its host (qwen_rom_rt_w12_stream4_fulltoken.cpp is written for 4 dies)",
               "the TP8 die core: KV merged on the ROM die (track B, one die type) = the KV-die attention composed in the same simulation "
               "instead of the tile attention; the bit-plane vector memory (ot_qfd_sp_vector_memory_bv, XPR / XQR)",
               "the TP8 relay case (stage counts per bus of the TP8 floorplan) once the relay plan is final",
               "a TP8 price: results/arch/token_path_20261009/qwen_rom.json is the TP4 path (6,835 cycles a layer)"],
        cheapest="the TP4 vehicle at the priced die station / stage counts (this record: terms.issue_plus_die) + the KV-die head group bench "
                 "for the attention swap: it covers the three die-level terms (623 + 428 of 432 + 266 = 1,317 of the 1,355 cycles the "
                 "s22ml7 vehicle lacks) with no new fixture.  It does NOT cover TP 8 itself (rank count, 8-way all-reduce, TP8 floorplan "
                 "stage counts, bit-plane VM other than through the XVM / BD probes)")

    tp8["unmeasured_after_this_record"] = [
        "the 8-rank shape itself: 8-way all-reduce (allreduce1 / allreduce2 are 2,100 of the 6,835 priced cycles, measured at N 4), "
        "8-rank weight partition (768 / 512 / 768 rows a die) and its golden: no fixture, no 8-die harness",
        "the TP8 floorplan's relay stage counts (bd / tree / tws / ord / link per bus): this record measures the r21 TP4 counts",
        "the merged-die attention INSIDE the layer simulation: the vehicle runs the tile attention (1,550 of its 5,480 cycles); the "
        "merged sequencer is measured on its own vehicle and added (this is why record.json says 57.5 %: 3,930 of the 6,835 "
        "production cycles are the same RTL function in the vehicle; with the die-term runs 4,981 = 72.9 %; with the sequencer "
        "bench 6,797 = 99.4 % of the priced cycles have a measurement on SOME vehicle; 38 stay priced)",
        "the bit-plane vector memory in the layer simulation (measured as an x-read latency, QROM_XVM / QROM_BD, and on its own "
        "system bench: XVM 38 = +14 at XPR 10 / XQR 2); the placed XPR is not final",
        "the hardened qfd_* / qkd_* tiles composed (no simulation composes them), head on the die composition (3,048 on the stationed core)"]
    tp8["closes_with_the_die_leads_relay_count"] = (
        "the die lead posts the TP8 case's stage counts per bus class (relay_token_cost of tools/qwen_rom_fulldie_b3r2.py on the "
        "final relay plan: bd = head chain + corridor + tap, tree, tws, ord, link) -> ONE run of results/rtl/qwen_layer_tput_1013/"
        "die_terms/qjob.sh with QROM_BD / QROM_TWS / QROM_ORD / QROM_LAT at those counts (+ QROM_XVM = 1 + XPR + XQR + 3 - RO, "
        "QROM_BD += the same), --su-ml 15, ~2.5 h on ot-epyc1tb: the measured layer at the TP8 die's relay depth, exact against the "
        "TP4 golden.  That closes the relay and VM-latency share of the TP8 layer; it does NOT close the 8-rank all-reduce (needs "
        "the N 8 collective bench at production FIFOs against its own price) or the 8-rank golden.  Pair-check candidates so far: "
        "spine_local +2 x 217 ME ops, stack_local +2 x 72 link traversals = at most +939 cycles a token (0.43 %), "
        "results/arch/pinreg_audit_1013/pairs/qwen_rom_tp8.md")
    scope = dict(vehicle="TP4 cycle-reference core at stated station/stage counts; no native TP8 vehicle exists",
                 measured_fraction="fraction of priced cycle subtotal represented by reference measurements, not physical or eight-rank functional coverage",
                 cost_status="analytic graph composition of measured layer deltas on the committed token path; ledger rows qwen_rom DIE.RELAY and VM.XREAD (PROPOSED)")

    out = dict(schema="opentallas.qwen_layer_die_terms.v1", source_sha=a.sha, base_record=str(REC.relative_to(ROOT)),
               base_layer=dict(vehicle="s22ml7", stage_cycles=base, priced=base["L1"]),
               priced_terms=dict(issue_relays_r22k=P_ISSUE, die_relays_430um=P_DIE, die_relays_in_vehicle=in_vehicle,
                                 kv_die_attention_swap=P_KV, r21_stage_counts=R21),
               runs=runs, terms=terms, mutant=mutant, kv_attention_swap=kv_swap, composed_production_layer=comp,
               handoffs=hand, tp8_vehicle=tp8, measurement_scope=scope,
               registry=dict(issue_relays=dict(elements="^(qfd_sp_tree_top|qfd_tt_)", ratio=terms["issue_relays"].get("ratio")),
                             die_relays=dict(elements="^(qfd_rly|qfd_lst_)", ratio=terms["die_relays"].get("ratio"))))
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    for k, t in terms.items():
        print(k, {x: t.get(x) for x in ("status", "exact", "measured_layer", "priced_layer", "ratio", "measured_delta", "priced_delta", "delta_ratio")})
    print("mutant", mutant)
    print("composed", comp)


if __name__ == "__main__":
    main()
