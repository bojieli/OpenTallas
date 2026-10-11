#!/usr/bin/env python3
"""Top-down per-unit throughput budget + qualification table (AGENTS.md "Throughput qualification", owner 2026-10-10).

For each unit / op class on each target's dataflow:
  budget   = the simulator price the token is charged for the op (per record and per token, S2 schedule), scaled to
             the target table rate, plus the items / cycle the unit must sustain at that price (production shape);
  measured = the production-shape throughput bench (RTL cycles over the same records' price) -> ratio;
  status   = QUALIFIED (ratio <= 1.10) | UNQUALIFIED (ratio > 1.10) | UNQUALIFIED_NO_BENCH (no production-shape number);
  impact   = the token cycles the op's measured ratio costs on the S2 schedule (op scaled alone, everything else at
             price) -- the bottleneck rank.  A unit qualifies only with a committed production-shape bench.

    python3 -m throughput_budget.build --out results/arch/throughput_budget_20261010/budget.json      (from tools/)

Inputs (all committed): the G25 DS rank-0 program + bit-exact run (results/arch/hgi_sim_20261010/g25_proof), the
e2e / unit-bench calibration (results/arch/hgi_sim_20261009/e2e_calibration.json), the budget audit
(results/arch/budget_audit_20261010/table.json), the ROM token paths (results/arch/token_path_20261009), and the
MEASURED table below (each entry cites its committed record or the stream log line for interim numbers).
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import timing as T  # noqa: E402

CLK = 1.2e9
QUAL = 1.10                     # owner rule: measured within 10 % of the price it is charged
DS_TARGET = 2208.1              # DS AR table rate (budget_audit targets.hbm_compute.DS_AR_native)
DS_MTP_TAU = 4.159
QWEN_TARGET = 953.8

PROG = ROOT / "results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json"
RUN = ROOT / "results/arch/hgi_sim_20261010/g25_proof/ds_full.json"
CAL = ROOT / "results/arch/hgi_sim_20261009/e2e_calibration.json"
AUDIT = ROOT / "results/arch/budget_audit_20261010/table.json"
TP = ROOT / "results/arch/token_path_20261009"

# ---------------------------------------------------------------------------------------------------------------
# Measured production-shape benches.  grade: unit_bench | e2e (die e2e, all-real units, production width) |
# price_fit (the price IS the measured form) | interim_log (stream log number, not committed: never qualifies).
# ratio = RTL cycles / simulator price on the same records.
U = "results/rtl/hgi_unit_tput_20261010/"
MEASURED = {
    "COLL.ALL_GATHER": dict(ratio=0.716, grade="unit_bench", src=U + "coll/report.json",
                            note="ot_hgi_coll_ep PIPE=1 on the 13 DS L0 gather records (main 86ee9156a / ca33eaa6e)"),
    "COLL.GROUP_REDUCE_MCAST": dict(ratio=0.908, grade="e2e", src="results/rtl/hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93/report.json",
                                    note="one record, die e2e all-real"),
    "COLL.ROW_GATHER": dict(ratio=1.0, grade="price_fit", src="main 5e588e11e (hgi-1010/a, G25 HW ROW_GATHER, one real rank of 96)",
                            note="price = K x F / 4 + 150 fitted to the measured 4,242 cycles at K 512"),
    "SU.VOP": dict(ratio=1.067, grade="unit_bench", src=U + "su/report.json",
                   note="27-record DS L0 SU chain, production width"),
    "DMA.LOAD": dict(ratio=0.622, grade="e2e", src="results/rtl/hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93/report.json",
                     note="6 records"),
    "DMA.FENCE": dict(ratio=0.117, grade="e2e", src="results/rtl/hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93/report.json"),
    "DMA.KVWB_DS": dict(ratio=3.817, grade="e2e", src="results/rtl/hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93/report.json",
                        note="retires on write completion, not acceptance (audit hbm_ds_kvwb)"),
    "FUSED.HC_PRE_NORM": dict(ratio=6.514, grade="unit_bench", src=U + "fused/hc_pre_norm_d5120/report.json"),
    "FUSED.HC_POST": dict(ratio=20.085, grade="unit_bench", src=U + "fused/hc_post_d5120/report.json"),
    "FUSED.QDQ_FP8": dict(ratio=14.573, grade="unit_bench", src=U + "qdq/ds_L0_tput/report.json"),
    "FUSED.QDQ_FP4_E8M0": dict(ratio=8.167, grade="unit_bench", src=U + "qdq/ds_L0_tput/report.json"),
    "FUSED.QDQ_FP4_E4M3": dict(ratio=14.583, grade="unit_bench", src=U + "qdq/ds_L0_tput/report.json"),
    "HC.HC_MIX_POST": dict(ratio=1.282, grade="unit_bench", src=U + "hc/ds_L0_tput/report.json"),
    "HC.HC_MIX_ROWS": dict(ratio=125.155, grade="unit_bench", src=U + "hc/ds_L0_tput/report.json",
                           interim=dict(ratio=round(482 / 193.3, 3), src="hgi-1010.log 20:04 d: striped fetch SPL 4 (32 lanes) 6,052 -> 482 cyc/record")),
    "HC.HC_MIX": dict(ratio=64.931, grade="unit_bench", src=U + "hc/ds_L0_tput/report.json"),
    "IDX.TOPK": dict(ratio=4.286, grade="unit_bench", src=U + "idx/ds_L0_tput/report.json",
                     interim=dict(ratio=None, src="hgi-1010.log 20:50 g2: TOPKW=1 heap IW4/W4 under test (heap n49152 IW4 23.3k)")),
    "IDX.OWNED": dict(ratio=1.004, grade="unit_bench", src=U + "idx/ds_L0_tput/report.json"),
    "IDX.INDEX": dict(ratio=None, grade=None, src=None,
                      interim=dict(ratio=1.36, src=U + "iks/README.md: key-stream issuer q0 460 vs 339 priced (one stack; not the whole record)")),
    "ATT.QK": dict(ratio=None, grade=None, src=None,
                   interim=dict(ratio=None, src="main a7613320f ATT PIPE=2: H4 D128 NL2 vehicle QK T512 1,951 cyc (not DS production shape hd512 / 1M)")),
    "ATT.PV": dict(ratio=None, grade=None, src=None,
                   interim=dict(ratio=None, src="main a7613320f ATT PIPE=2: PV T512 2,968 cyc (vehicle, not production shape)")),
    "SM.MATVEC": dict(ratio=None, grade=None, src=None,
                      interim=dict(ratio=None, src="hgi-1010.log 20:04: SM DS ratio rerun with tb_hgi_sm_tput on exp_2c9860e12 -> d (pending)")),
}
# Qwen-on-HBM ops: the audit's measured rows (Qwen-shape benches) where they exist
MEASURED_QWEN = {
    "SU.VOP": dict(ratio=2.896, grade="e2e", src="budget_audit table.json qwen_su_sfu (measured rtl/sim)"),
    "SFU.GLU": dict(ratio=2.896, grade="e2e", src="budget_audit table.json qwen_su_sfu (SU/SFU staging, same row)"),
    "DMA.LOAD": dict(ratio=9.204, grade="e2e", src="budget_audit table.json hbm_dma_load"),
    "DMA.STORE": dict(ratio=round(129.0 / 30, 3), grade="e2e", src="budget_audit table.json hbm_qwen_dma_store"),
    "COLL.ALL_REDUCE_SUM": dict(ratio=round(1230 / 1350, 3), grade="e2e", src="budget_audit table.json hbm_qwen_allreduce"),
    "SM.MATVEC": dict(ratio=round(2762 / 1372.0, 3), grade="unit_bench",
                      src="budget_audit table.json qwen_sm_xload_serial (2,762 measured vs 1,372 designed a record)"),
    "ARGMAX.LOCAL": dict(ratio=round(96502 / 76394, 3), grade="e2e", src="budget_audit table.json qwen_head_stream_chain"),
}

# unit.op -> owner stream raising its throughput (from the stream logs, 2026-10-10 evening)
OWNERS = {
    "HC.HC_MIX_ROWS": "hgi-1010/d (striped SPL4 482 cyc) + c (HC weight DMA prefetch, kport RB 64) + e (compiler prefetch)",
    "HC.HC_MIX": "hgi-1010/d",
    "HC.HC_MIX_POST": "hgi-1010/d",
    "FUSED.HC_POST": "hgi-1010/b (FUSED UWIDE / wide VM lanes)",
    "FUSED.HC_PRE_NORM": "hgi-1010/b (FUSED UWIDE / wide VM lanes)",
    "FUSED.QDQ_FP8": "tput-gate-1010 (taken 10-10: QDQ on the FUSED lgE lane group, 32 elements/cycle; c keeps the packet transport)",
    "FUSED.QDQ_FP4_E8M0": "tput-gate-1010 (with QDQ_FP8)",
    "FUSED.QDQ_FP4_E4M3": "tput-gate-1010 (with QDQ_FP8)",
    "IDX.TOPK": "hgi-1010/g2 (TOPKW=1 heap, 9473077de)",
    "IDX.INDEX": "hgi-1010/g2 (idx chunk) + hbm-phys-1010 (IKS svc stripe) + e (IKS compiler c9d5c8dea)",
    "DMA.KVWB_DS": "hgi-1010/c (posted KVWB retire 87b97e35e merged; ratio predates it: regrade with DMA_POSTED) + e (e2e)",
    "ATT.QK": "hgi-1010/g2 (ATT PIPE=2 a7613320f; wide VM wclient open)",
    "ATT.PV": "hgi-1010/g2",
    "SM.MATVEC": "hgi-1010/d (tb_hgi_sm_tput) + fe-push-hgi-1010 (sm_xload SRAM + FP8 x-path)",
    "SU.VOP": "hgi-1010/b",
    "COLL.ALL_GATHER": "hgi-1010/c + fe-push-hgi-1010 (parking SRAM)",
    "COLL.ROW_GATHER": "hgi-1010/c",
    "COLL.TOPK_MERGE": "tput-gate-1010 (taken 10-10: production-shape bench)",
    "COLL.ARGMAX_MERGE": "UNOWNED",
    "ARGMAX.LOCAL": "UNOWNED",
    "CP.FETCH": "hbm-phys-1010 [svc] (native burst, NATIVE_NO 16 bee505fe4; loader routes) + hgi-1010/e (e2e model)",
}

# unit.op -> registry elements (fleet-viz /api/elements master names) whose throughput the op's bench qualifies
ELEMENTS = {
    "SU.VOP": ["ot_hgi_su_record", "ot_hgi_su_ctl", "ot_hgi_su_ctlw", "hfd_su_tile", "hfd_su_tile_xl", "hfd_su_result_ingress"],
    "SFU.GLU": ["ot_hgi_sfu_record", "hfd_sfu_tile", "hfd_sfu"],
    "FUSED.HC_PRE_NORM": ["ot_hgi_fused_record"],
    "FUSED.HC_POST": ["ot_hgi_fused_record"],
    "FUSED.QDQ_FP8": ["hfd_quant", "ot_hgi_quant_decode", "ot_hgi_quant_vm_transport_p"],
    "HC.HC_MIX_ROWS": ["ot_hgi_hc_record", "ot_hgi_hc_unit", "hfd_hc"],
    "HC.HC_MIX_POST": ["ot_hgi_hc_record", "ot_hgi_hc_unit", "hfd_hc"],
    "IDX.TOPK": ["hgi_idx_topk_full", "hgi_idx_topk_heap"],
    "IDX.INDEX": ["hfd_idx_score", "hfd_idx_t4_join", "hfd_idx_sel_native_qend", "hfd_index_q_b0", "hfd_index_q_b1",
                  "hfd_index_q_b2", "hfd_index_q_b3", "hfd_index_q_b5", "hgi_idx_chunk", "ot_hdc_v41x_idx_chunk_el"],
    "ATT.QK": ["hgi_att_record_g12_320", "hgi_att_record_g12_360", "hgi_att_rows_g12_120", "hgi_att_rows_g12_140",
               "ot_hgi_att_issue", "ot_hgi_att_sector_codec", "hfd_attn_half_hi", "hfd_attn_half_lo", "ot_attn_tile_m6h1q"],
    "SM.MATVEC": ["ot_hgi_sm_record", "ot_hgi_sm_xload", "ot_hgi_sm_pub", "ot_hbm_accel_smh_be_eg", "ot_hbm_accel_smh_be_wg",
                  "ot_hbm_accel_smh_front_n", "ot_hbm_accel_smh_front_s", "ot_hbm_accel_smh_front_c",
                  "ot_hbm_accel_smh_tile_eg", "ot_hbm_accel_smh_tile_wg"],
    "COLL.ALL_GATHER": ["hfd_coll", "ot_hgi_coll_decode", "hfd_coll_pkt_fifo_ii1", "hfd_coll_credit_prod", "hfd_coll_idle_tx"],
    "COLL.ROW_GATHER": ["ot_hgi_coll_row_formatter"],
    "DMA.KVWB_DS": ["ot_hgi_dma_mover", "ot_hgi_dma_record", "ot_hgi_dma_front"],
    "ARGMAX.LOCAL": ["ot_hgi_argmax18_m", "ot_hgi_argmax_record"],
    "CP.FETCH": ["ot_hgi_cp", "ot_hgi_seq", "hfd_cmdproc_n", "hfd_cmdproc_s", "hfd_loader"],
    "VM.PORTS": ["ot_hgi_vm_unit", "hfd_vm_ne_e", "hfd_vm_ne_w", "hfd_vm_nw_e", "hfd_vm_nw_w", "hfd_vm_se_e", "hfd_vm_se_w",
                 "hfd_vm_sw_e", "hfd_vm_sw_w", "hfd_vm_ne_s"],
    "MTP.VERIFY": ["hgi_mtp_native", "ot_hgi_mtp_core18", "ot_hgi_mtp_accept18", "hfd_mtp_x_stop", "ot_hgi_cp_mtp_pinreg"],
    "SVC.STREAM": ["hfd_svc_SE_s%d" % i for i in range(9)] + ["hfd_svc_SW_s%d" % i for i in range(8)],
}


def status_of(ratio, grade):
    if ratio is None or grade in (None, "interim_log"):
        return "UNQUALIFIED_NO_BENCH"
    return "QUALIFIED" if ratio <= QUAL else "UNQUALIFIED"


def items_of(r):
    """(items, what) a record moves / computes at production shape"""
    u, op = r.unit, r.op
    d = r.desc
    if u == "SM" or (u == "ATT"):
        b = d.get("B")
        return (b.n * b.m, "MACs (weight / key elements)") if b else (0, "")
    if u == "IDX" and op == "INDEX":
        return (r.imm_a or d["A"].n, "keys scored")
    if u in ("DMA", "COLL"):
        a = d.get("A")
        if not a:
            return (0, "")
        n = a.n * a.m
        if op == "ROW_GATHER":
            n *= (r.imm_a or 1)
        return (n * T.ESZ[a.fmt], "bytes")
    if not d:
        return (0, "")
    x = max(d.values(), key=lambda x: x.n * x.m)
    return (x.n * x.m, "elements (largest operand)")


def ds_budget():
    from hgi_sim import ds_native_timing as DT
    d, recs = DT.load(PROG)
    recs = T.rebuild_waits(recs)
    rg = {}
    for x in json.loads(RUN.read_text())["results"]:
        for s_ in x.get("row_gather") or []:
            rg[x["layer"]] = s_
    DT.apply_dyn_counts(recs, rg)
    cf = DT.NativeCost(d["ops"], recs, row_gather=rg)
    acc = collections.defaultdict(lambda: dict(n=0, cyc=0.0, items=0, what="", layers=collections.Counter(), recs=[]))

    def rec_cf(r, dyn, L):
        c = cf(r, dyn, L)
        k = f"{r.unit}.{r.op}"
        a = acc[k]
        a["n"] += 1
        a["cyc"] += c[0]
        it, what = items_of(r)
        a["items"] += it
        a["what"] = what or a["what"]
        a["layers"][getattr(r, "layer", None)] += c[0]
        return c

    base = T.schedule(recs, DT.POS, "S2", cost_fn=rec_cf)
    S2 = base["total_cycles"]
    per_unit = base["per_unit"]
    scale_to_target = (CLK / DS_TARGET) / S2      # uniform: every price x this hits the table rate

    def sched_with(k, f):
        def g(r, dyn, L):
            c = cf(r, dyn, L)
            return (c[0] * f if f"{r.unit}.{r.op}" == k else c[0]), c[1], c[2]
        return T.schedule(recs, DT.POS, "S2", cost_fn=g)["total_cycles"]

    rows = []
    for k, a in sorted(acc.items(), key=lambda kv: -kv[1]["cyc"]):
        if k.startswith("CTL."):
            continue
        m = MEASURED.get(k, {})
        ratio = m.get("ratio")
        grade = m.get("grade")
        st = status_of(ratio, grade)
        # sensitivity: d(token)/d(op price) at +10 %, and the token cost of the measured ratio
        el = (sched_with(k, 1.10) - S2) / S2
        impact = (sched_with(k, ratio) - S2) if ratio not in (None, 1.0) else 0.0
        nl = len([L for L in a["layers"] if L is not None])
        price_rec = a["cyc"] / a["n"]
        rows.append(dict(
            op=k, unit=k.split(".")[0], records_per_token=a["n"], layers_with_op=nl,
            price_cycles_per_record=round(price_rec, 1), price_cycles_per_token=round(a["cyc"], 1),
            price_cycles_per_layer=round(a["cyc"] / max(nl, 1), 1),
            budget_cycles_per_record_at_target=round(price_rec * scale_to_target, 1),
            items_per_record=round(a["items"] / a["n"], 1), item=a["what"],
            required_items_per_cycle=round(a["items"] / a["cyc"], 3) if a["cyc"] else None,
            required_items_per_cycle_at_target=round(a["items"] / (a["cyc"] * scale_to_target), 3) if a["cyc"] else None,
            share_of_unit_busy=None,
            token_elasticity_at_plus10pct=round(el, 5),
            measured_ratio=ratio, measured_grade=grade, measured_src=m.get("src"), measured_note=m.get("note"),
            interim=m.get("interim"),
            measured_cycles_per_record=round(price_rec * ratio, 1) if ratio else None,
            status=st,
            impact_cycles_per_token=round(impact, 1),
            impact_tok_s=round(CLK / (S2 + impact) - CLK / S2, 1) if impact else 0.0,
            owner=OWNERS.get(k, "-"), elements=ELEMENTS.get(k, []),
        ))
    # unmeasured ops: rank by price x elasticity (a 2x shortfall would cost this much)
    for r in rows:
        if r["status"] == "UNQUALIFIED_NO_BENCH":
            r["exposure_cycles_if_2x"] = round(r["token_elasticity_at_plus10pct"] * 10 * S2, 1)
    from hgi_sim.records import encode_program
    return dict(S2_cycles=round(S2, 1), S2_tok_s=round(CLK / S2, 1), target_tok_s=DS_TARGET,
                image_bytes=len(encode_program(recs)),
                target_cycles=round(CLK / DS_TARGET, 1), price_scale_to_target=round(scale_to_target, 4),
                per_unit_S2=per_unit, ops=rows, program=str(PROG.relative_to(ROOT)), run=str(RUN.relative_to(ROOT)))


def qwen_budget():
    from hgi_sim import qwen_compiler as QC
    cfg = json.loads((ROOT / "compiler/models/qwen3-8b/config.json").read_text())
    recs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg["num_hidden_layers"])
    acc = collections.defaultdict(lambda: dict(n=0, cyc=0.0, items=0, what=""))

    def rec_cf(r, dyn, L):
        c = T.cost(r, dyn, L)
        a = acc[f"{r.unit}.{r.op}"]
        a["n"] += 1
        a["cyc"] += c[0]
        it, what = items_of(r)
        a["items"] += it
        a["what"] = what or a["what"]
        return c

    S2 = T.schedule(recs, 8191, "S2", cost_fn=rec_cf)["total_cycles"]
    sc = (CLK / QWEN_TARGET) / S2

    def sched_with(k, f):
        def g(r, dyn, L):
            c = T.cost(r, dyn, L)
            return (c[0] * f if f"{r.unit}.{r.op}" == k else c[0]), c[1], c[2]
        return T.schedule(recs, 8191, "S2", cost_fn=g)["total_cycles"]

    rows = []
    for k, a in sorted(acc.items(), key=lambda kv: -kv[1]["cyc"]):
        if k.startswith("CTL."):
            continue
        m = MEASURED_QWEN.get(k, {})
        ratio, grade = m.get("ratio"), m.get("grade")
        impact = (sched_with(k, ratio) - S2) if ratio not in (None, 1.0) else 0.0
        el = (sched_with(k, 1.10) - S2) / S2
        pr = a["cyc"] / a["n"]
        rows.append(dict(op=k, unit=k.split(".")[0], records_per_token=a["n"],
                         price_cycles_per_record=round(pr, 1), price_cycles_per_token=round(a["cyc"], 1),
                         price_cycles_per_layer=round(a["cyc"] / cfg["num_hidden_layers"], 1),
                         budget_cycles_per_record_at_target=round(pr * sc, 1),
                         items_per_record=round(a["items"] / a["n"], 1), item=a["what"],
                         required_items_per_cycle=round(a["items"] / a["cyc"], 3) if a["cyc"] else None,
                         token_elasticity_at_plus10pct=round(el, 5),
                         measured_ratio=ratio, measured_grade=grade, measured_src=m.get("src"),
                         status=status_of(ratio, grade), impact_cycles_per_token=round(impact, 1),
                         impact_tok_s=round(CLK / (S2 + impact) - CLK / S2, 1) if impact else 0.0,
                         owner=OWNERS.get(k, "hgi-1010"), elements=ELEMENTS.get(k, [])))
    return dict(S2_cycles=round(S2, 1), S2_tok_s=round(CLK / S2, 1), target_tok_s=QWEN_TARGET,
                price_scale_to_target=round(sc, 4), ops=rows,
                note="Qwen on HBM is deprioritised (runs exactly; TOKEN_SAVE 10-10); ratios are the audit's Qwen-shape "
                     "measurements")


def rom_budget(name):
    d = json.loads((TP / f"{name}.json").read_text())
    tot = d["totals"]["cycles"]
    by = collections.defaultdict(lambda: dict(cycles=0.0, nodes=0, grades=collections.Counter(), unmeasured=[]))
    for n in d["nodes"]:
        c = by[n["cls"]]
        c["nodes"] += 1
        c["grades"][n["src"]["grade"]] += n["cycles"]
        if n.get("critical"):
            c["cycles"] += n["cycles"]
        if not n["src"]["grade"].startswith("measured") and n["cycles"] > 0:
            c["unmeasured"].append(n["id"])
    cls_el = {c["id"]: c["elements"] for c in d["classes"]}
    rows = []
    for k, c in sorted(by.items(), key=lambda kv: -kv[1]["cycles"]):
        unm = sum(v for g, v in c["grades"].items() if not g.startswith("measured"))
        allc = sum(c["grades"].values())
        # node prices are measured RTL unit cycles at production shape: a class qualifies when >= 95 % of its cycles
        # are measured; its few modelled nodes are listed as their own unbenched gaps (unmeasured_nodes)
        st = "QUALIFIED" if allc and unm / allc <= 0.05 else "UNQUALIFIED_NO_BENCH"
        rows.append(dict(cls=k, critical_cycles_per_token=round(c["cycles"], 1),
                         share=round(c["cycles"] / tot, 4), nodes=c["nodes"],
                         measured_fraction=round(1 - unm / allc, 4) if allc else None,
                         unmeasured_nodes=c["unmeasured"][:12], n_unmeasured=len(c["unmeasured"]),
                         status=st, elements=cls_el.get(k, []),
                         basis="token-path node prices are the measured RTL unit cycles at production shape "
                               "(grade 'measured'); 'modelled' / 'priced' / 'apportioned' nodes have no bench"))
    stages = [g for g in d["groups"] if g.get("kind") in ("stage", "layer", "embed")]
    worst = max(stages, key=lambda g: g["cycles"]) if stages else None
    return dict(headline=d["headline"].get("tok_s"), cycles=tot, classes=rows,
                stage_ii_limiter=dict(id=worst["id"], label=worst["label"], cycles=worst["cycles"]) if worst else None,
                n_stages=len(stages), source=str((TP / f"{name}.json").relative_to(ROOT)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ds = ds_budget()
    print("DS S2", ds["S2_cycles"], ds["S2_tok_s"], flush=True)
    qw = qwen_budget()
    print("Qwen S2", qw["S2_cycles"], qw["S2_tok_s"], flush=True)
    audit = json.loads(AUDIT.read_text())
    rom = {"qwen_rom": rom_budget("qwen_rom"), "ds_rom": rom_budget("ds_rom")}
    rom_audit = [dict(id=r["id"], target=r["target"], unit=r["unit"], metric=r.get("metric"), required=r.get("required"),
                      measured=r.get("measured"), margin=r.get("margin"), flag=r.get("flag"), owner=r.get("owner_stream"))
                 for r in audit["rows"] if r["target"] in ("qwen_rom", "ds_rom")]
    # non-op data / control rows (CP fetch, KV, svc) from the audit, DS first
    dc = [dict(id=r["id"], target=r["target"], unit=r["unit"], metric=r.get("metric"), required=r.get("required"),
               designed=r.get("designed"), measured=r.get("measured"), margin=r.get("margin"), flag=r.get("flag"),
               ratio=(round(1 / r["margin"], 3) if isinstance(r.get("margin"), (int, float)) and r["margin"] else None),
               owner=r.get("owner_stream"), confidence=r.get("confidence"))
          for r in audit["rows"] if r["unit"] in ("CP.fetch", "KV_READ", "SVC", "DMA", "CP.dispatch") and r["target"].startswith("hbm")]
    # ranking: DS measured shortfalls by token cycles; then unmeasured by exposure
    rank = sorted([r for r in ds["ops"] if r["status"] == "UNQUALIFIED"], key=lambda r: -r["impact_cycles_per_token"])
    nob = sorted([r for r in ds["ops"] if r["status"] == "UNQUALIFIED_NO_BENCH"], key=lambda r: -r.get("exposure_cycles_if_2x", 0))
    ranking = [dict(rank=i + 1, op=r["op"], ratio=r["measured_ratio"], impact_cycles_per_token=r["impact_cycles_per_token"],
                    impact_tok_s=r["impact_tok_s"], budget_cycles_per_record=r["price_cycles_per_record"],
                    budget_at_target=r["budget_cycles_per_record_at_target"], owner=r["owner"]) for i, r in enumerate(rank)]
    # registry gate: element -> worst status over the ops it serves (DS first, then Qwen, then ROM classes)
    order = {"UNQUALIFIED": 0, "UNQUALIFIED_NO_BENCH": 1, "QUALIFIED": 2}
    el = {}

    def put(e, target, op, st, ratio, owner, src):
        cur = el.get(e)
        ent = dict(op=op, model=target, status=st, ratio=ratio, owner=owner, src=src)
        if cur is None:
            el[e] = dict(status=st, ratio=ratio, limiting=ent, ops=[ent])
        else:
            cur["ops"].append(ent)
            if order[st] < order[cur["status"]] or (order[st] == order[cur["status"]] and (ratio or 0) > (cur["ratio"] or 0)):
                cur.update(status=st, ratio=ratio, limiting=ent)

    for r in ds["ops"]:
        for e in r["elements"]:
            put(e, "DS AR 1M (HBM)", r["op"], r["status"], r["measured_ratio"], r["owner"], r["measured_src"])
    for r in qw["ops"]:
        for e in r["elements"]:
            put(e, "Qwen AR 8K (HBM)", r["op"], r["status"], r["measured_ratio"], r["owner"], r["measured_src"])
    cp = next((x for x in dc if x["id"] == "hbm_ds_cp_fetch"), None)
    for e in ELEMENTS["CP.FETCH"]:
        put(e, "DS AR 1M (HBM)", "CP.FETCH", "UNQUALIFIED" if cp and (cp["ratio"] or 0) > QUAL else "UNQUALIFIED_NO_BENCH",
            cp["ratio"] if cp else None, OWNERS["CP.FETCH"], "budget_audit hbm_ds_cp_fetch (0.867 B/cyc needed, 0.308 designed)")
    for e in ELEMENTS["VM.PORTS"]:
        put(e, "DS AR 1M (HBM)", "VM.PORTS", "UNQUALIFIED_NO_BENCH", None, "hgi-1010/b (wide VM lanes)",
            "no production-shape VM lane-group bench against the client budget yet")
    for e in ELEMENTS["MTP.VERIFY"]:
        put(e, "DS MTP (HBM)", "MTP.VERIFY", "UNQUALIFIED_NO_BENCH", None, "hgi-1010/h + bf-mtp-1010",
            "hgi-1010.log 20:22 h: L0 verify 5 cols ~145k RTL vs 63.8k sim (interim); no native DS verify program")
    ws = next((x for x in dc if x["id"] == "hbm_qwen_weight_stream"), None)
    for e in ELEMENTS["SVC.STREAM"]:
        put(e, "Qwen AR 8K (HBM)", "SVC.STREAM", "QUALIFIED" if ws else "UNQUALIFIED_NO_BENCH",
            round(1 / ws["margin"], 3) if ws else None, "hbm-phys-1010", "budget_audit hbm_qwen_weight_stream (0.775 needed vs 0.862 bench)")
    for name, rb in rom.items():
        for c in rb["classes"]:
            for e in c["elements"]:
                put(e, name, "class:" + c["cls"], c["status"], None, "-", rb["source"])
    # HBM loader / svc endpoint budget (DS AR, per die and per stack of 4): bytes per token from the program, the rate a
    # record needs at its price, and the overlap-aware token average (owner bandwidth rule: derive the minimum)
    opb = {r["op"]: r for r in ds["ops"]}
    tc = CLK / DS_TARGET
    svc = {}
    for k, kind in (("DMA.LOAD", "read"), ("DMA.KVWB_DS", "write"), ("COLL.ROW_GATHER", "write (head-die HBM row write)")):
        r = opb.get(k)
        if not r:
            continue
        b = r["items_per_record"] * r["records_per_token"]
        svc[k] = dict(kind=kind, bytes_per_token=round(b), at_price_B_per_cycle_die=r["required_items_per_cycle"],
                      at_price_B_per_cycle_stack_striped=round(r["required_items_per_cycle"] / 4, 3),
                      token_average_B_per_cycle_die=round(b / tc, 3))
    cpr = next((x for x in dc if x["id"] == "hbm_ds_cp_fetch"), None)
    svc["CP.FETCH"] = dict(kind="read", bytes_per_token=d_img if (d_img := ds.get("image_bytes")) else None,
                           required_B_per_cycle_die=cpr["required"] if cpr else None,
                           designed_B_per_cycle_die=cpr["designed"] if cpr else None,
                           note="budget_audit hbm_ds_cp_fetch: ring fetch of the unrolled image, overlap-aware minimum")
    rec = dict(schema="opentallas.throughput_budget.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule="AGENTS.md Throughput qualification (owner 2026-10-10, main 8a62d15ae): a unit qualifies only when "
                    "bit-exact + timing-closed + a production-shape throughput bench is within 10 % of its simulator price",
               qualify_ratio=QUAL,
               hbm_bandwidth_rule="no fixed fraction of HBM peak; fetches are overlapped as the S2 schedule models; "
                                  "a weight / KV path needs only its overlap-aware minimum (owner 10-10 06:58)",
               targets=dict(ds_ar=DS_TARGET, ds_mtp=dict(tau=DS_MTP_TAU, fixed_rtl_tok_s=3640.3,
                                                         source="results/arch/hgi_sim_20261010/ds_rates_g25.json"),
                            qwen_ar=QWEN_TARGET, qwen_rom=rom["qwen_rom"]["headline"], ds_rom=rom["ds_rom"]["headline"]),
               ds_hbm=ds, ds_bottleneck_ranking=ranking,
               ds_unbenched_by_exposure=[dict(op=r["op"], exposure_cycles_if_2x=r.get("exposure_cycles_if_2x"),
                                              price_cycles_per_token=r["price_cycles_per_token"], owner=r["owner"],
                                              interim=r.get("interim")) for r in nob],
               hbm_datactl_rows=dc, svc_endpoint_budget_ds=svc, qwen_hbm=qw, rom=rom, rom_audit_rows=rom_audit,
               elements=dict(sorted(el.items())))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    for x in ranking:
        print(x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
