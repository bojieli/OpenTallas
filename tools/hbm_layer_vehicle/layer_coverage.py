#!/usr/bin/env python3
"""TOKEN-PASS-HBMDS (10-18): which records of a representative DS layer can run on the d4g die RTL of record.

For every record of the compiler's static schedule (priced_layers.json, d4g_2ring_qbg) it names the d4g die masters
that execute it and the die-contract GAPS (pre.json["gaps"]: inputs with no real producer, issuers / loaders /
datapath joins missing on main) that block a native run.  A record is RUNNABLE only if every master is bound in the
die contract AND no blocking gap is open; else BLOCKED (gap ids).  The layer's priced cycles are attributed to each
grade by the record's schedule span on the critical chain (end - start of records; overlap counted once by a sweep).
    layer_coverage.py --priced priced_layers.json --contract pre.json[.gz] --out coverage.json
"""
import argparse, gzip, json
from collections import defaultdict

Q = ("SW", "SE", "NW", "NE")
HOST = ["G-CIL-HOSTN", "G-HOST-PROGRAM-INSTALL"]          # no host packet bridge / programme install on the die
# orig_op -> (die masters that execute it, gaps that block it natively)
UNIT = {
    "SM.MATVEC": (["ot_hbm_accel_smh_attn", "ot_hgi_sm_xload_cl2_bfqg", "ot_hbm_svc_sm_group_id", "ot_hbm_svc_sm_xcal_t",
                   "ot_hbm_svc_pc_ctrl_leaf_cfg_h9b", "ot_hbm3e_phy_rc_e8p5"],
                  ["G-SMVM-XCMD", "G-HOST-LOADER-SVG", "G-HOST-LOADER-CAL", "G-SMVM-CALISS"]),
    "ATT.QK": (["ot_hbm_accel_smh_attn", "ot_hbm_svc_sm_group_id", "ot_hbm3e_phy_rc_e8p5"],
               ["G-SMVM-XCMD", "G-HOST-LOADER-SVG", "G-HOST-LOADER-CAL"]),
    "ATT.PV": (["ot_hbm_accel_smh_attn", "ot_hbm_svc_sm_group_id", "ot_hbm3e_phy_rc_e8p5"],
               ["G-SMVM-XCMD", "G-HOST-LOADER-SVG", "G-HOST-LOADER-CAL"]),
    "SU.VOP": (["ot_hbm_su_programme_pslice_c5", "ot_hbm_su_static_qcore", "ot_hbm_su_static_pgslice_lg",
                "ot_hbm_su_stree_root"], ["G-SU-PROG-HOST", "G-SMVM-CALISS"]),
    "FUSED.HC_PRE_NORM": (["ot_hbm_hc_bankq_static", "ot_hbm_hc_qhub_static", "ot_hbm_hc_root_static"], ["G-HC-ENG", "G-HC"]),
    "FUSED.HC_POST": (["ot_hbm_hc_bankq_static", "ot_hbm_hc_qhub_static"], ["G-HC-ENG", "G-HC"]),
    "HC.HC_MIX": (["ot_hbm_hc_bankq_static", "ot_hbm_hc_qhub_static", "ot_hbm_hc_root_static"], ["G-HC-ENG", "G-HC"]),
    "FUSED.QDQ_FP8": (["ot_hgi_qdq_host_split"], ["G-QUANT-SPLIT"]),
    "COLL.ALL_GATHER": (["ot_hfd_coll_q2_hard_v8g", "ot_hfd_coll_q3_hard_v8x", "ot_hgi_coll_gq_issue", "ot_hgi_coll_gq_land",
                         "ot_hgi_coll_ring_b_stop", "hfd_ep_static", "ot_pdie_serdes"],
                        ["G-CIL-INJ", "G-CIL-DEL", "G-CIL-COLLSTAT"]),
    "COLL.GROUP_REDUCE_MCAST": (["ot_hfd_coll_q2_hard_v8g", "ot_hfd_coll_q3_hard_v8x", "hfd_ep_static", "ot_pdie_serdes"],
                                ["G-CIL-INJ", "G-CIL-DEL", "G-CIL-RC", "G-CIL-COLLSTAT"]),
    "COLL.ROW_GATHER": (["ot_hfd_coll_q2_hard_v8g", "ot_hfd_coll_q3_hard_v8x", "hfd_ep_static"], ["G-CIL-DEL", "G-CIL-COLLSTAT"]),
    "COLL.TOPK_MERGE": (["ot_hgi_coll_tkm_m_tp192", "ot_hfd_coll_q3_hard_v8x"], ["G-CIL-INJ", "G-CIL-COLLSTAT"]),
    "COLL.ARGMAX_MERGE": (["ot_hfd_coll_q3_hard_v8x"], ["G-CIL-INJ", "G-CIL-COLLSTAT", "G-CIL-AMCP"]),
    "DMA.LOAD": (["ot_hgi_dma_back_static_vp4_banks_cp", "ot_hbm_svc_vmdel_lane_n", "ot_hbm_svc_vm_kshare_splitstrap",
                  "ot_hbm3e_phy_rc_e8p5"], ["G-DMA", "G-HOST-LOADER-CAL"]),
    "DMA.KVWB_DS": (["ot_hgi_dma_back_static_vp4_banks_cp", "ot_hbm_svc_wb_kport_q", "ot_hbm3e_phy_rc_e8p5"],
                    ["G-DMA", "G-DMA-WB"]),
    "DMA.FENCE": (["ot_hgi_dma_back_static_vp4_banks_cp"], ["G-DMA"]),
    "IDX.TOPK": (["ot_hbm_idx_selector_static", "ot_hbm_idx_topk_link_static", "ot_hbm_idx_rootctl_static"], ["G-CIL-IDXCP"]),
    "IDX.INDEX": (["ot_hbm_idx_score_quarter_static", "ot_hbm_idx_query_static", "ot_hbm_idx_vm_query_static",
                   "ot_hbm_idx_qctl_static", "ot_hbm_idx_xq_node_static", "ot_hbm_idx_selector_static"], ["G-CIL-IDXCP"]),
    "ARGMAX.LOCAL": (["ot_hbm_argmax_static_sw_vm"], ["G-CIL-AMCP"]),
    "CTL.NOP": ([], []),
}
# loader / issuer / status gaps a vehicle TB may stand in for with compiler images written at the target's programme
# port (declared external stimulus) -- everything else is an on-chip DATAPATH gap no TB may fill (all-onchip rule)
LOADER = {"G-CIL-HOSTN", "G-HOST-PROGRAM-INSTALL", "G-HOST-LOADER-CAL", "G-HOST-LOADER-SVG", "G-SMVM-CALISS",
          "G-SU-PROG-HOST", "G-CIL-IDXCP", "G-CIL-AMCP", "G-CIL-COLLSTAT"} | {f"G-SFU-LOADER-{q}" for q in Q}
SFU_OPS = ("swiglu", "router_act", "attend.exp_sum", "attend.max")     # SU templates that use the SFU in the DS lowering
# measured unit benches that bear on these records (NOT on the d4g die; component evidence only)
UNIT_BENCH = {
    "SM.MATVEC": "SM bx L0/L1/IH 5,760/6,392/22,320 cycles exact (357764a5c, results/rtl/hbm_b2_1012/summary.json) on the hgi SM "
                 "adapter, not ot_hbm_accel_smh_attn in the d4g die",
    "ATT.QK": "tb_hgi_att_tput (fd655cde6) ot_hgi_att_unit: service 0.992x / 0.808x of price, T512 QK 2,604 / PV 4,190",
    "ATT.PV": "tb_hgi_att_tput (fd655cde6) as ATT.QK",
    "COLL.ALL_GATHER": "tb_hgi_coll_ring_ag ring MODE 0 F 224 -> 342 edges, F 112 -> 174 (r = 0); collq_gather_1018 gq span "
                       "1 + 3((K-1)>>1) + ((K-1)&1) + 38",
    "SU.VOP": "tb_hbm_su_programme_pgcol c5 lockstep vs r4 on the 7,111-edge su_top_compile image (31 su_arith classes, "
              "synthetic vectors, not DS layer records)",
    "IDX.INDEX": "results/rtl/tput_map_1011/hbm_idx_redesign/evidence_1013/phase_L{2,20,24} (pre-quadrant IDX)",
}


def sweep(iv):
    iv = sorted(i for i in iv if i[1] > i[0])
    tot, cur = 0.0, None
    for a, b in iv:
        if cur is None or a > cur[1]:
            if cur:
                tot += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    return tot + (cur[1] - cur[0] if cur else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--priced", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    P = json.load(open(a.priced))
    C = json.load((gzip.open if a.contract.endswith(".gz") else open)(a.contract, "rt"))
    # HBM-WIRE 10-18: gaps the contract marks closed (status "closed" + closed_by, d4g_functional_bind) no longer block
    gaps = {g["id"]: g for g in C["gaps"] if str(g.get("status", "open")).lower() != "closed"}
    bound = {i["master"] for i in C["instances"].values()}
    layers = {}
    names = {"0": "L0 (first layer: CSA attention + MoE FFN, no indexer)", "2": "L2 (CSA + indexer IDX.INDEX)",
             "14": "L14 (Engram)", "3": "L3 (MoE FFN layer, attention without indexer)", "head": "LM head (AR)",
             "1": "L1"}
    for L, seg in P["segments"].items():
        rows, by_grade, gap_cycles = [], defaultdict(list), defaultdict(list)
        for r in seg["records"]:
            op = r["orig_op"]
            if op == "CTL.END":
                continue
            ms, gs = UNIT.get(op, ([], ["UNMAPPED"]))
            gs = list(gs)
            if op == "SU.VOP" and r["tag"].startswith(SFU_OPS):
                gs += [f"G-SFU-LOADER-{q}" for q in Q] + [f"G-SFU-OPERAND-JOIN-{q}" for q in Q]
                ms = ms + ["ot_hgi_sfu_core_split3", "ot_hgi_sfu_programme_store_r10"]
            if op != "CTL.NOP":
                gs += HOST
            open_g = sorted({g for g in gs if g in gaps or g == "UNMAPPED"})
            unbound = sorted({m for m in ms if m not in bound})
            grade = "NO_HW" if op == "CTL.NOP" else ("RUNNABLE" if not open_g and not unbound else "BLOCKED")
            dp = sorted(g for g in open_g if g not in LOADER)
            if grade == "BLOCKED" and not dp and not unbound:
                grade = "TB_IMAGE_LOAD_ONLY"
            iv = (r["start"] or 0.0, r["end"] or 0.0)
            by_grade[grade].append(iv)
            for g in open_g:
                gap_cycles[g].append(iv)
            rows.append(dict(i=r["i"], op=op, tag=r["tag"][:60], start=r["start"], end=r["end"], grade=grade,
                             masters=ms, unbound_masters=unbound, open_gaps=open_g, datapath_gaps=dp, unit_bench=UNIT_BENCH.get(op)))
        dpc = defaultdict(list)
        for x in rows:
            for g in x["datapath_gaps"]:
                dpc[g].append((x["start"] or 0.0, x["end"] or 0.0))
        span = seg["cycles"]
        layers[L] = dict(name=names.get(L, L), priced_cycles=span, records=len(rows),
                         grade_records={g: len(v) for g, v in by_grade.items()},
                         grade_span_cycles={g: round(sweep(v), 1) for g, v in by_grade.items()},
                         runnable_fraction_of_layer=round(sweep(by_grade.get("RUNNABLE", [])) / span, 4) if span else 0,
                         gap_span_cycles={g: round(sweep(v), 1) for g, v in sorted(gap_cycles.items(), key=lambda kv: -sweep(kv[1]))},
                         datapath_gap_span_cycles={g: round(sweep(v), 1) for g, v in sorted(dpc.items(), key=lambda kv: -sweep(kv[1]))},
                         rows=rows)
    out = dict(schema="opentallas.hbm_ds_layer_coverage.v1", priced=a.priced, contract=a.contract,
               contract_summary=C["summary"], gaps={g: dict(owner=v.get("owner"), missing_rtl=v.get("missing_rtl", "")[:400])
                                                     for g, v in gaps.items()}, layers=layers)
    json.dump(out, open(a.out, "w"), indent=1)
    for L, v in layers.items():
        print(f"{L:>4} priced {v['priced_cycles']:>9} rec {v['records']:>3} grades {v['grade_records']} "
              f"runnable {v['runnable_fraction_of_layer']:.1%}\n      datapath gaps (span) {v['datapath_gap_span_cycles']}")


if __name__ == "__main__":
    main()
