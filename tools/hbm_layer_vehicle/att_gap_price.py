#!/usr/bin/env python3
"""HBM-ATTGAP (10-19): re-price the d4g DS AR token for the three attention gaps of VEH-ATT and their options.

Base: results/rtl/hbm_ds_layer_tput_1018/priced_layers.json (d4g_2ring_qbg, 629,775.1 cycles = 1,905.4 tok/s): 38 T640
layers (ATT.QK base 547, ATT.PV base 808) + 2 T128 layers (411 / 580); attend.qk -> SU max/exp_sum/bf16_p -> attend.pv ->
attend.norm is serial on every layer's critical path (priced_layers start/end), so a record's added cycles add to the
token (ledger rule: the unit at its measured cycles, everything else at price).

Terms (cycles at 1.2 GHz; serial-domain edges x 4/3):
  measured   SM boundary span (first command word -> last result) on the die SM master (att_images.py unit): busiest SM
             (window KV8).  One op a SM: QK 684 / PV 839 (VEH-ATT); sub-runs: sum of the sub-run spans + the issuer
             go bubble between programme segments (GO_BUBBLE).
  merge      on-die cross-SM PV merge (SU lane-store tree + COLL ring all-gather + top levels fused into attend.norm),
             previously unpriced: MERGE model below (edges from the RTL constants the bench uses).
  window     staging refresh by DMA: off the critical path (a token of slack) -> 0 token cycles; DMA / HBM busy reported.
Options for the programme gap: S32 (chosen, compiler only), BIGPROG (programme SRAM 2,048 words in the svg W135 / xc W173
stores + issuer prog_base/limit +1 bit: no cycle cost, SM-service tile change), RELOAD (programme reinstall through the
host CP ingress: 61k edges a SM op, infeasible), SPLIT (QK / PV on different SMs: needs 20 SMs or > 1,024-word programmes).

    att_gap_price.py --unit L2_s32_pos.json --out price.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PL = ROOT / "results/rtl/hbm_ds_layer_tput_1018/priced_layers.json"
CLK = 1.2e9
SER = 4.0 / 3.0                 # serial-domain edge in stream cycles (3:4, AGENTS clock domains)
GO_BUBBLE = 5                   # issuer FIXED_GO go -> calendar word: start_v_q, running, valid0, valid1, calendar
VEH_ATT = dict(qk=684, pv=839)  # one op a SM, busiest SM (KV8), VEH-ATT 07a99bc0a unit/L2_pos.json
# SU edge constants (layer_images.py / tb_su_static_arithmetic / pslice): start advance DEPTH+4, VM fill commit E+13,
# drain done +7, die lane issue->output LATENCY 23+4(MLAT-3)+(ALAT-3)+LEAF (MLAT 4, ALAT 3, LEAF 1) + 2 pin-reg edges,
# lane-store read consumed n+3; quarter = 128 lanes, VM fill 8 sectors (64 words) an edge.
SU_START, SU_FILL, SU_DRAIN, SU_LAT, SU_STORE_RD = 5, 13, 7, 23 + 4 + 0 + 1 + 2, 3
RING_FLIT_B, RINGS, NQ = 32, 2, 4


def ag_cycles(nbytes, r_hop):
    """d4g on-die ring all-gather (d4g_quadrant_1017.ag_cycles: min of MODE 0 1.5F + 3 hops, MODE 1 2F + 2 hops)."""
    F = -(-nbytes // NQ // (RING_FLIT_B * RINGS))
    hop = 2 + r_hop
    return min(1.5 * F + 3 * hop, 2 * F + 2 * hop)


def merge_cycles(nodes_q, levels_q, levels_top, r_hop):
    """critical cycles after the last SM publishes: quadrant programme (fill trails the smw writes; chained levels in the
    lane store; drain of the partial), ring all-gather of the 4 partials, top levels fused into attend.norm."""
    groups = 512 // 128
    l1 = (nodes_q // 2) * groups
    chain = l1
    n = nodes_q // 2
    for _ in range(levels_q - 1):
        n //= 2
        chain += SU_LAT + SU_STORE_RD + max(1, n) * groups
    q_prog = SU_START + SU_FILL + chain + SU_LAT + 2 * groups + SU_DRAIN
    ag = ag_cycles(NQ * 512 * 4, r_hop)
    top = 2 * 1 + SU_FILL + levels_top * (SU_LAT + SU_STORE_RD) + 1      # 4 partial slices in, chained top levels
    return dict(quadrant_programme_edges=q_prog, quadrant_programme=round(q_prog * SER, 1), ring_all_gather=round(ag, 1),
                top_levels_edges=top, top_levels_in_norm=round(top * SER, 1),
                total=round(q_prog * SER + ag + top * SER, 1))


def ledger_rows(doc, price_path, evidence, merge_status):
    """r25gq (HBM die) rows of the three d4g attention terms, each priced alone against the d4g base (ledger rule)."""
    import sys
    sys.path.insert(0, str(ROOT / "tools" / "throughput"))
    import accepted_cost as AC
    led = AC.load_ledger()
    base, n640, n128 = doc["base_cycles"], doc["t640_layers"], doc["t128_layers"]
    s32, one = doc["subrun_busiest"], doc["measured_one_op"]
    rel = lambda p: str(Path(p).resolve().relative_to(ROOT)) if Path(p).resolve().is_relative_to(ROOT) else str(p)  # noqa: E731

    def pw(added, model):
        return dict(ds_ar=dict(model=model, base_cycles=base, cycles=round(base + added, 1), added_cycles=round(added, 1),
                               e2e_loss_pct=round(AC.loss_pct(base, base + added), 3)))
    rows = []
    a1 = n640 * ((one["qk"] - 547) + (one["pv"] - 808))
    rows.append(AC.make_row("r25gq", "ATT.D4G.SPAN: ATT.QK + ATT.PV on the d4g die SM master (GEN2b ot_hbm_accel_smh_attn, "
                            "real DS L2 rows, busiest SM KV8), per T640 layer", 547 + 808, one["qk"] + one["pv"],
                            pw(a1, "d4g price5 priced_layers: attend.qk/pv serial on every T640 layer's critical path; "
                                   "the record at its measured span (first command word -> last result)"),
                            "results/rtl/hbm_ds_layer_tput_1018/veh_att_1019/unit/L2_pos.json", "committed_bench",
                            note=f"VEH-ATT 07a99bc0a: 20/20 ops bit-exact; QK 684 (KV8) / 660 (KV4), PV 839 / 815 vs base "
                                 f"547 / 808; {n640} T640 layers (T128 not measured, kept at price). HBM-ATTGAP 10-19.",
                            group="ATT.D4G.SPAN"))
    a2 = n640 * ((s32["qk"] - one["qk"]) + (s32["pv"] - one["pv"]))
    rows.append(AC.make_row("r25gq", "ATT.D4G.SUBRUN32: QK / PV as two 32-row sub-runs a SM (programme residency: one "
                            "resident QK + PV copy, 1,019 / 971 of 1,024 words; no RTL)", 0, round(a2 / n640, 1),
                            pw(a2, "sub-run spans summed + issuer go bubble 5, minus the one-op spans, per T640 layer"),
                            evidence or rel(price_path), "committed_bench",
                            note="replaces a 1,531-word one-op programme that cannot be resident (1,024-word svg/xc "
                                 "programme SRAM; reinstall ~61k ingress edges a SM op). Alternative BIGPROG (2,048-word "
                                 "programme stores, SM-service tile re-close) would save this row; not taken (closure "
                                 "first, owner: HBM accepts AR loss without numerics change). Window staging refresh "
                                 "(DMA, 0 critical cycles) removes per-token descriptor/programme changes. HBM-ATTGAP 10-19.",
                            group="ATT.D4G.SUBRUN32"))
    a3 = n640 * doc["merge_t640"]["total"] + n128 * doc["merge_t128"]["total"]
    rows.append(AC.make_row("r25gq", "ATT.D4G.PV_MERGE: on-die cross-SM ATT.PV merge (SU lane-store pairwise tree + COLL "
                            "ring all-gather + top levels in attend.norm; previously unpriced)", 0,
                            doc["merge_t640"]["total"],
                            pw(a3, "SU edge model from the RTL constants of the merge bench (start 5, fill +13, lane "
                                   "LAT 30, store read +3, drain +7, 3:4 serial) + d4g ring all-gather (ag_cycles)"),
                            evidence or rel(price_path), "committed_bench",
                            note=("exactness benched on the real N512 SU arithmetic with the RTL PV nodes (golden pairwise "
                                  "tree incl. +0 pads, final == fixture PV): " + merge_status + "; cycles MODELLED (not a "
                                  "die run). HBM-ATTGAP 10-19."),
                            group="ATT.D4G.PV_MERGE"))
    for r in rows:
        r["share_basis"] = "modelled"
        AC.propose(led, r)
    try:
        AC.supersede(led, "r25gq", r"^ATT$", by="d4g price5 (547/808 are the d4g base_cost) + ATT.D4G.* rows",
                     reason="HBM-ATTGAP 10-19: the A-price composition of this row is retired by the d4g price; the d4g "
                            "die measurements are the ATT.D4G rows")
    except AC.LedgerError:
        pass
    AC.save_ledger(led)
    print("LEDGER rows", [(r["group"], r["e2e_loss_pct"]) for r in rows], "totals", json.dumps(led["totals"]["r25gq"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--unit", default="", help="att_images.py unit --subrun result json (measured sub-run spans)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger", action="store_true", help="write the ATT.D4G.* rows into the accepted-cost ledger")
    ap.add_argument("--evidence", default="", help="committed evidence path of the sub-run / merge benches")
    ap.add_argument("--merge-status", default="RTL bench pending", help="state of the att_merge_su.py RTL bench")
    a = ap.parse_args(argv)
    pl = json.loads(PL.read_text())
    base = pl["ar_cycles"]
    r_hop = pl["knob"]["r_hop"]
    t640 = [k for k, s in pl["per_segment"].items() if k != "head"]
    seg = pl["segments"]
    # T640 / T128 layer census from the priced records (QK base 547 vs 411)
    rep = {k: (k if k in seg else "3") for k in t640}
    n640 = sum(1 for k in t640 if next(r for r in seg[rep[k]]["records"] if r["orig_op"] == "ATT.QK")["base_cost"] == 547)
    n128 = len(t640) - n640
    price = dict(qk=547, pv=808)
    meas_src = "model (calendar words - 9 / + 1, VEH-ATT span law)"
    sub = dict(qk=[428, 428], pv=[583, 583])
    if a.unit:
        u = json.loads(Path(a.unit).read_text())
        sp = u["summary"]["spans_first_word_to_last_result"]
        busiest = max(sp, key=lambda s: sum(sp[s]["qk"]) + sum(sp[s]["pv"]))
        sub = dict(qk=sp[busiest]["qk"], pv=sp[busiest]["pv"])
        meas_src = f"{a.unit} ({u['summary']['verdict']}, busiest {busiest})"
    s32 = {k: sum(v) + GO_BUBBLE * (len(v) - 1) for k, v in sub.items()}
    m640 = merge_cycles(8, 3, 2, r_hop)            # 20 sub-run nodes: 8 / 8 / 4+4 pads / 8 pads -> 3 levels + 2 top
    m640_one = merge_cycles(4, 2, 2, r_hop)        # 10 SM nodes (one op a SM): 4 / 4 / 2+2 / 4 -> 2 levels + 2 top
    m128 = merge_cycles(4, 2, 2, r_hop)            # T128: 16 SM nodes of 8 rows, 4 a quadrant
    rows = {}

    def opt(name, qk, pv, merge, n128_add, note, feasible=True):
        d = n640 * ((qk - price["qk"]) + (pv - price["pv"]) + merge) + n128 * n128_add
        tok = base + d
        rows[name] = dict(feasible=feasible, qk_cycles=qk, pv_cycles=pv, merge_cycles=merge,
                          added_per_t640_layer=round((qk - price["qk"]) + (pv - price["pv"]) + merge, 1),
                          added_cycles=round(d, 1), token_cycles=round(tok, 1), ds_ar_tok_s=round(CLK / tok, 1),
                          ds_ar_loss_pct=round(100 * (1 - base / tok), 3), note=note)

    opt("as_priced", 547, 808, 0, 0, "d4g price5 base (merge unpriced, programme residency assumed)")
    opt("S32_chosen", s32["qk"], s32["pv"], m640["total"], m128["total"],
        "32-row sub-runs (one resident QK + PV programme, 1,019 / 971 words), SU merge of 20 nodes, window staging "
        "refresh by DMA (0 critical); compiler + DMA only, NO RTL change")
    opt("BIGPROG", VEH_ATT["qk"], VEH_ATT["pv"], m640_one["total"], m128["total"],
        "programme SRAM 2,048 words (svg W135 + xc W173 stores of all 16 SMs, issuer prog_base/limit +1 b): one op a "
        "SM at the VEH-ATT spans; SM-service tile re-close")
    opt("measured_only", VEH_ATT["qk"], VEH_ATT["pv"], 0, 0,
        "information: the die-master spans alone (programme residency and merge ignored)")
    reload_edges = 61240                      # VEH-ATT plan: 1,531 words x 40 edges (svg + xc) a SM op
    opt("RELOAD", VEH_ATT["qk"] + reload_edges, VEH_ATT["pv"] + reload_edges, m640_one["total"], 0,
        "programme reinstall through the shared host CP ingress per op (~61k edges a SM op, x10 SMs serial on one "
        "ingress at best ~61k exposed a op): infeasible", feasible=False)
    rows["SPLIT"] = dict(feasible=False, note="QK and PV on different SMs: PV needs 10 SMs (nrun 8, golden subtree), the "
                                              "6 left would need 107 rows a QK (KV8 > 1,024 words) -> no fit in 16 SMs")
    dma_bytes = 2 * 67056 + 528
    doc = dict(schema="opentallas.hbm_attgap_price.v1", lane="HBM-ATTGAP", base=str(PL.relative_to(ROOT)),
               base_cycles=base, base_tok_s=round(CLK / base, 1), t640_layers=n640, t128_layers=n128,
               price=price, measured_one_op=VEH_ATT, measured_subrun_spans=sub, measured_subrun_source=meas_src,
               subrun_busiest=s32, go_bubble=GO_BUBBLE, merge_t640=m640, merge_t640_one_op=m640_one, merge_t128=m128,
               window_staging=dict(critical_cycles=0, dma_bytes_per_layer_token=dma_bytes,
                                   dma_busy_cycles_per_layer_est=round(2 * (104 + 67056 / 396.0), 1),
                                   note="refresh (VM load + store of 127 rows) between this token's attend.pv and the next "
                                        "token's append of the layer; 396 B/cycle = 4 quadrant PCs x 99"),
               options=rows, chosen="S32_chosen",
               breakdown_chosen=dict(measured_excess_one_op=n640 * ((VEH_ATT["qk"] - 547) + (VEH_ATT["pv"] - 808)),
                                     subrun=n640 * ((s32["qk"] - VEH_ATT["qk"]) + (s32["pv"] - VEH_ATT["pv"])),
                                     merge=round(n640 * m640["total"] + n128 * m128["total"], 1)))
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    if a.ledger:
        ledger_rows(doc, a.out, a.evidence, a.merge_status)
    print(json.dumps({k: (v["ds_ar_tok_s"], v.get("ds_ar_loss_pct")) if isinstance(v, dict) and "ds_ar_tok_s" in v
                      else v.get("feasible") for k, v in rows.items()}))
    print(json.dumps(doc["breakdown_chosen"]), json.dumps(m640))
    return 0


if __name__ == "__main__":
    main()
