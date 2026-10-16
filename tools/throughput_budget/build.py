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
import re
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
    "COLL.ROW_GATHER": dict(ratio=round(4233 / 4246.0, 3), grade="unit_bench", src="results/rtl/hgi_rgx_pipe_merge_20261010/rgx_matrix_SUMMARY.txt",
                            note="g96_b1 G96 K512: 4,233 cycles vs the 4,246 price (K x F / 4 + 150)"),
    "SU.VOP": dict(ratio=1.067, grade="unit_bench", src=U + "su/report.json",
                   note="27-record DS L0 SU chain, production width"),
    "DMA.LOAD": dict(ratio=0.622, grade="e2e", src="results/rtl/hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93/report.json",
                     note="6 records"),
    "DMA.FENCE": dict(ratio=0.117, grade="e2e", src="results/rtl/hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93/report.json"),
    "DMA.KVWB_DS": dict(ratio=3.817, grade="e2e", src="results/rtl/hgi_e2e_20261010/runs/ds_L0_g24_allreal_4bc04ba93/report.json",
                        note="retires on write completion, not acceptance (audit hbm_ds_kvwb)"),
    "FUSED.HC_PRE_NORM": dict(ratio=6.514, grade="unit_bench", src=U + "fused/hc_pre_norm_d5120/report.json"),
    "FUSED.HC_POST": dict(ratio=20.085, grade="unit_bench", src=U + "fused/hc_post_d5120/report.json"),
    "FUSED.QDQ_FP8": dict(ratio=2.74, grade="unit_bench", src=U + "qdq_wide/report.json",
                          note="ot_hgi_quant_unit WIDE (lane group) at the price of record ceil(n/32)+8; packet unit was 14.6x"),
    "FUSED.QDQ_FP4_E8M0": dict(ratio=4.5, grade="unit_bench", src=U + "qdq_wide/report.json"),
    "FUSED.QDQ_FP4_E4M3": dict(ratio=2.75, grade="unit_bench", src=U + "qdq_wide/report.json"),
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
# HAND-ENTERED (main 10-10): these Qwen ratios were copied from budget_audit rows, not from a committed bench record of
# this unit at Qwen shape -> grade 'hand_entered': shown as a claim, never qualifying; listed in build_gate['hand_entered'].
MEASURED_QWEN = {
    "SU.VOP": dict(ratio=2.896, grade="hand_entered", src="budget_audit table.json qwen_su_sfu (measured rtl/sim)"),
    "SFU.GLU": dict(ratio=2.896, grade="hand_entered", src="budget_audit table.json qwen_su_sfu (SU/SFU staging, same row)"),
    "DMA.LOAD": dict(ratio=9.204, grade="hand_entered", src="budget_audit table.json hbm_dma_load"),
    "DMA.STORE": dict(ratio=round(129.0 / 30, 3), grade="hand_entered", src="budget_audit table.json hbm_qwen_dma_store"),
    "COLL.ALL_REDUCE_SUM": dict(ratio=round(1230 / 1350, 3), grade="hand_entered", src="budget_audit table.json hbm_qwen_allreduce"),
    "SM.MATVEC": dict(ratio=round(2762 / 1372.0, 3), grade="hand_entered",
                      src="budget_audit table.json qwen_sm_xload_serial (2,762 measured vs 1,372 designed a record)"),
    "ARGMAX.LOCAL": dict(ratio=round(96502 / 76394, 3), grade="hand_entered", src="budget_audit table.json qwen_head_stream_chain"),
}

# unit.op -> owner stream raising its throughput (from the stream logs, 2026-10-10 evening)
OWNERS = {
    "HC.HC_MIX_ROWS": "hgi-1010/d (striped SPL4 482 cyc) + c (HC weight DMA prefetch, kport RB 64) + e (compiler prefetch)",
    "HC.HC_MIX": "hgi-1010/d",
    "HC.HC_MIX_POST": "hgi-1010/d",
    "FUSED.HC_POST": "hgi-1010/b (FUSED UWIDE / wide VM lanes)",
    "FUSED.HC_PRE_NORM": "hgi-1010/b (FUSED UWIDE / wide VM lanes)",
    "FUSED.QDQ_FP8": "tput-gate-1010 (WIDE built + benched 1.01x; route + hb_quant lgE slot-2 share open)",
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


# DS ROM BF of record (owner 10-10/11): hierarchical full-rate BF = ot_v41_bf_col (column) + ot_s81_bf_front (front),
# compact variants; HALF_PHL (ot_s81_bf_native) is the fallback.  Price (tools/s81/bf_hier_price.py hier_compact): the
# full-rate element + HIER 3 cycles on every BF-busy region phase (partials: column boundary register +1, BXST/FXST relays
# +2).  Exact benches (results/rtl/s81_bf_arch_20261009/bench, same 456-row / 232-partial workload):
#   tcg0 (flat full-rate QZE, the price basis)  issue 124,422 cyc, partial lag mean 6.591 / max 12.495 ns
#   hcol (column + front, HCOL=1)               issue 124,422 cyc, partial lag mean 9.090 / max 14.994 ns
#   -> issue cycles identical (ratio 1.000); partial lag +2.499 ns = +3.0 cycles at 833.3 ps (priced HIER 3: ratio 1.000)
BF_HIER = dict(
    status="QUALIFIED", ratio=1.0,
    target=dict(ds_rom_ar_tok_s=1553.4, ds_rom_mtp_tok_s=4443.6, row="hier_compact on the current base",
                condition="Option A (compact column + front <= 198.72 um tall, pair <= 1,031.6 um); else HALF_PHL fallback",
                src="results/rtl/s81_bf_arch_20261009/compose/price.json"),
    budget=dict(issue_cycles=124422, issues=4288, partials=232, rows=456, partial_extra_cycles=3,
                rule="full-rate issue (the flat element's cycles on the bench workload) + 3 cycles a partial (HIER)"),
    measured=dict(issue_cycles=124422, partial_lag_extra_ns_mean=round(9.090 - 6.591, 3),
                  partial_lag_extra_ns_max=round(14.994 - 12.495, 3), partial_extra_cycles=3.0,
                  benches=["results/rtl/s81_bf_arch_20261009/bench/tcg0.json", "results/rtl/s81_bf_arch_20261009/bench/hcol.json",
                           "results/rtl/s81_bf_arch_20261009/bench/full.json"]),
    timing=dict(ot_v41_bf_col="bfh_col600_28fa6290c-cl CLOSED TT +34.26 / FF +0.67 (compact col: bfh_compact220_col_a1200)",
                ot_s81_bf_front="bfh_compact220_front_a1200_84d63c93f-cl CLOSED TT +87.90 / FF +9.98 (main 943cad2b2)",
                composed="results/rtl/s81_bf_arch_20261009/compose/summary.json: interface TT +265.8 / FF +45.1 balanced"),
    src="results/rtl/s81_bf_arch_20261009/bench/{tcg0,hcol}.json + compose/price.json")

# ROM blocks outside every token-path class: (regex, model, class, forced status or None = the class's, ratio, why)
ROM_RULES = [
    (r"^ot_s81_bf_native$", "ds_rom", "field", None, None, "bf-hier-1011: HALF_PHL BF, now the fallback (field class)"),
    (r"^(dsfd_m2l_|dsfd_l2r_|dsfd_r2l_|dsfd_stn|dsfd_hstnh_|ot_meso_fifo_|ot_dsrom_ring_dyn)", "ds_rom", "field", None, None,
     "ds-1010: field relays / stations (measured field phases include the wire)"),
    (r"^(dsfd_cap_mtp|dsfd_coll_mtp|dsfd_coll_p2|dsfd_mtp_|dsfd_vm_mtp|dsfd_vm_p2|dsfd_vm_wfc|dsfd_wfc_|dsfd_p2_lnk|dsrom_mtp_|"
     r"ot_dsrom_mtp_|ot_dsrom_wfc_|ot_mtp_|ot_dsrom_markov_)", "ds_rom_mtp", "wave", "UNQUALIFIED_NO_BENCH", None,
     "bf-mtp-1010: DS ROM MTP draft / WFC / accept path not integrated on the S81 binding (audit dsrom_mtp_draft_hw)"),
    (r"^dsfd_coll_", "ds_rom", "coll", None, None, "ds-1010: collective lanes"),
    (r"^(dsfd_engram_)", "ds_rom", "embed", None, None, "ds-1010: engram lookup / sink (embed class)"),
    (r"^(ot_dsrom_hc_|dsfd_sp_hc_|ot_dsrom_su_)", "ds_rom", "su", None, None, "ds-1010: HC / SU lanes (su class)"),
    (r"^ot_hdc_v41_fh_", "ds_rom", "head", None, None, "ds-1010: final head (head class)"),
    (r"^(ot_s81_native_pc_mux|dsfd_svc|dsfd_ctrl)", "ds_rom", "hbm", None, None, "ds-1010: HBM PC path (hbm class)"),
    (r"^(dsfd_host|ot_s81_host_dispatch|ot_s81_ingest_visibility)", "ds_rom", "host", "UNQUALIFIED_NO_BENCH", None,
     "ds-1010: host / ingest path: no per-token price row (prefill / admission), no throughput bench"),
    (r"^(qkd_|ot_qkvd_|qfd_kv|ot_qwen_rom_core_core_kv|qfd_su_kv|ot_qwen_nearhbm_)", "qwen_rom", "kv_die", "UNQUALIFIED_NO_BENCH", None,
     "qwen-1010/b: KV die / attention step: the 1.124 hand rule (superseded audit model) is REMOVED; qwen-1010/b replaces it with the measured KV-die record"),
    (r"^(qfd_coll_xfifo|qfd_cdc|ot_qwen_stream4_cdc)", "qwen_rom", "link", None, None, "qwen-1010: link / collective FIFOs (link class)"),
    (r"^(qfd_ctrl_|qfd_emb_pc|qfd_pc_head|qfd_tt_|qfd_crom_|qfd_q5_|qfd_row_merge)", "qwen_rom", "me", None, None,
     "qwen-1010: tile-tree / PC control of the matrix engine (me class)"),
    (r"^(qfd_res_|qfd_cst|qfd_seq_su|qfd_sp_constants|qfd_su_cbuf|qfd_sysctl|qfd_io_host)", "qwen_rom", "su", None, None,
     "qwen-1010: spine SU / sequencer / residual (su class)"),
    (r"^qfd_dspark_", "qwen_rom", "mtp", "UNQUALIFIED_NO_BENCH", None, "qwen-1010: DSpark on Qwen ROM has no qualified composition"),
]


def rom_blocks():
    """ROM-target element names from the live registry (fleet-viz /api/elements), else none (offline build)"""
    import urllib.request
    try:
        rows = json.load(urllib.request.urlopen("http://127.0.0.1:8765/api/elements", timeout=60))["rows"]
    except Exception:  # noqa: BLE001
        return []
    return sorted(r["element"] for r in rows if r["target"] in ("DeepSeek ROM", "Qwen ROM") and r["category"] != "superseded")


ROM_BLOCKS = rom_blocks()


def prov(path):
    """short commit of the last change to a committed record path, else None"""
    import subprocess
    if not path or not (ROOT / path).exists():
        return None
    out = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h", "--", path], capture_output=True, text=True).stdout.strip()
    return out or None


_CYC = re.compile(r"\b(cycles|CYCLES|cyc)\s*[=:]\s*(\d+)")
_ITEMS = re.compile(r"\b(beats|words|flits|rows|tuples|packets|elements|sectors|keys|transactions|requests|responses|reads|"
                    r"halves|bursts|issues|records|tokens|frames|blocks)\s*[=:]\s*(\d+)", re.I)


def bench_ii():
    """element -> the cycles-per-item line of its newest passing exact bench (closure-loop job state, CLOSED jobs first).
    The item kind is the largest-count item on the line; 'stalled' = the stimulus injects stalls (II not intrinsic)."""
    import glob as _g
    jd = Path.home() / ".local/state/closure_loop/jobs"
    best = {}
    for f in _g.glob(str(jd / "*.json")):
        try:
            j = json.loads(open(f).read())
        except Exception:  # noqa: BLE001
            continue
        if j.get("status") not in ("CLOSED",):
            continue
        blk = (j.get("spec") or {}).get("block")
        for bn, b in (j.get("benches") or {}).items():
            if b.get("expect") != "pass" or not b.get("ok"):
                continue
            for ln in (b.get("tail") or "").splitlines():
                m = _CYC.search(ln)
                if not m:
                    continue
                its = [(k.lower(), int(v)) for k, v in _ITEMS.findall(ln) if int(v) > 0]
                it = max(its, key=lambda x: x[1]) if its else None
                cyc = int(m.group(2))
                ent = dict(job=j["name"], commit=str(j.get("commit_full") or (j["spec"].get("source") or {}).get("commit", ""))[:9],
                           bench=bn, line=ln.strip()[:200], cycles=cyc, item=it[0] if it else None, items=it[1] if it else None,
                           ii=round(cyc / it[1], 3) if it else None, stalled=bool(re.search(r"stall|STALL|jitter", ln)),
                           owner=str((j.get("spec") or {}).get("owner", "")), target=None, t=j.get("updated", 0))
                if blk not in best or ent["t"] > best[blk]["t"]:
                    best[blk] = ent
                break
    return best


def variant_of(r):
    """record variant the build gate distinguishes: the SM x / weight format (fmt 1 FP8 / 2 FP4 block-dot: ot_hgi_sm_xload
    refuses them; 0 BF16 / 3 INT8 are built)"""
    if r.unit == "SM":
        return {0: "BF16", 1: "FP8", 2: "FP4", 3: "INT8"}[r.param & 3]
    return None


# ---- build gate (main 10-10 after hgi-1010 found COLL.TOPK_MERGE unbuilt): every op the simulator prices must have a
# bench that executes it NATIVELY in RTL (no stub, no behavioural model, no unsupported status).  Evidence: any committed
# report.json (unit bench / die e2e) with pass and a real, exact record of the op, else a curated record below.
CURATED = {
    "ATT.QK": ("BUILT", "results/hgi_attn_g12_20261009/exact_gate.a6.json (142 cases, DS128+2048, 1M linear rows) + results/rtl/hgi_adapters_20261009/benches/att_run.log (225 ATT records)"),
    "ATT.PV": ("BUILT", "results/hgi_attn_g12_20261009/exact_gate.a6.json + results/rtl/hgi_adapters_20261009/benches/att_run.log"),
    "COLL.ROW_GATHER": ("BUILT", "results/rtl/hgi_rgx_pipe_merge_20261010/rgx_matrix_SUMMARY.txt (G96 K512 / K2048 PASS, one real rank vs the switch model)"),
    "ARGMAX.LOCAL": ("BUILT", "results/rtl/hgi_adapters_20261009/benches/argmax_run.log (41 records, HGI_ARGMAX PASS)"),
    "SM.MATVEC|BF16": ("BUILT", "results/rtl/hgi_adapters_20261009/benches/sm_run.log + sm_bench_manifest.json (qwen3_8b_token_sm_matvec 145 records)"),
    "SM.MATVEC|INT8": ("BUILT", "results/rtl/hgi_adapters_20261009/benches/sm_bench_manifest.json (Qwen INT8 token records)"),
    "SM.MATVEC|FP8": ("NOT_BUILT", "rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv refuses x fmt 1 / 2 (x_fault): no FP8 block-dot x path "
                      "(audit ds_sm_xload_fp8_fp4_no_peer; FP8 x-path rebase = fe-push-hgi-1010 / hgi-1010/d)"),
    "SM.MATVEC|FP4": ("NOT_BUILT", "rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv refuses x fmt 2"),
    "COLL.TOPK_MERGE": ("NOT_BUILT", "rtl/hbm_accel/generic/collective/ot_hgi_coll_record.sv refuses op 2 ('merge stage not installed yet'); "
                        "the IDX.MERGE engine (ot_hgi_idx_merge) is not reachable from the record path"),
    "COLL.ARGMAX_MERGE": ("NO_NATIVE_EVIDENCE", "ot_hgi_coll_record op 3 + ot_hgi_coll_amerge exist; tb_hgi_coll_record checks only the endpoint "
                          "control with a stubbed endpoint (no exact native data run committed)"),
    "IDX.INDEX": ("NO_NATIVE_EVIDENCE", "ot_hgi_idx_index / _native exist; every committed die e2e runs IDX.INDEX as a stub (DS L2 with IDX stub); "
                  "only the IKS key-stream issuer is benched (hgi_unit_tput_20261010/iks)"),
    "CTL.NOP": ("BUILT", "CP (ot_hgi_cp / seq) in every die e2e"), "CTL.FENCE": ("BUILT", "CP in every die e2e"),
    "CTL.LOOP": ("BUILT", "CP in every die e2e"), "CTL.ENDLOOP": ("BUILT", "CP in every die e2e"), "CTL.END": ("BUILT", "CP in every die e2e"),
}


def native_evidence():
    """unit.op -> [report paths] with a passing, real, exact record of the op (committed reports in this tree)"""
    import hbm_generic_iface as HGI
    out = collections.defaultdict(list)
    for p in sorted(ROOT.glob("results/rtl/hgi_*/**/report.json")):
        try:
            d = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        if not d.get("pass_", d.get("pass", False)):
            continue
        for r in d.get("records") or []:
            if r.get("real") and r.get("mismatch", 0) == 0 and r.get("unit") in HGI.D_OPS:
                ops = HGI.D_OPS[r["unit"]]
                if isinstance(r.get("op"), int) and r["op"] < len(ops):
                    k = f"{r['unit']}.{ops[r['op']]}"
                    rel = str(p.relative_to(ROOT))
                    if rel not in out[k]:
                        out[k].append(rel)
    return out


NATIVE = None


def build_status(k, v):
    """(status, evidence) for priced op k (variant v)"""
    global NATIVE
    if NATIVE is None:
        NATIVE = native_evidence()
    key = f"{k}|{v}" if v else k
    if key in CURATED and CURATED[key][0] == "NOT_BUILT":
        return CURATED[key]
    if v is None and NATIVE.get(k):
        return "BUILT", "; ".join(NATIVE[k][:3])
    if key in CURATED:
        return CURATED[key]
    if NATIVE.get(k) and v is not None:
        return "BUILT", "; ".join(NATIVE[k][:3])
    return "NO_NATIVE_EVIDENCE", "no committed native bench of this op"


def BUILD_EVIDENCE_KEYS(acc):
    """(op, variant) pairs that are priced but not natively built (zero-cost re-schedules give their critical weight)"""
    out = []
    for k, a in acc.items():
        if k.startswith("CTL."):
            continue
        vs = [v for v in a["var"]] or [None]
        for v in vs:
            if build_status(k, v)[0] != "BUILT":
                out.append((k, v))
    return out


def status_of(ratio, grade):
    if ratio is None or grade in (None, "interim_log", "hand_entered"):
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
    acc = collections.defaultdict(lambda: dict(n=0, cyc=0.0, items=0, what="", layers=collections.Counter(), recs=[],
                                               var=collections.Counter(), varn=collections.Counter()))

    def rec_cf(r, dyn, L):
        c = cf(r, dyn, L)
        k = f"{r.unit}.{r.op}"
        a = acc[k]
        v = variant_of(r)
        a["var"][v] += c[0]
        a["varn"][v] += 1
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
        if st == "UNQUALIFIED_NO_BENCH" or (st == "UNQUALIFIED" and ratio is not None and ratio <= BOUND_SLOWDOWN):
            d10 = sched_with(k, BOUND_SLOWDOWN) - S2
            if d10 / S2 < BOUND_RATE and build_status(k, None)[0] == "BUILT":
                st = "QUALIFIED_BY_BOUND"
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
            variants={v: dict(records=a["varn"][v], price_cycles_per_token=round(c_, 1)) for v, c_ in a["var"].items()},
        ))
    # unmeasured ops: rank by price x elasticity (a 2x shortfall would cost this much)
    for r in rows:
        if r["status"] == "UNQUALIFIED_NO_BENCH":
            r["exposure_cycles_if_2x"] = round(r["token_elasticity_at_plus10pct"] * 10 * S2, 1)
    # build gate (main 10-10): token cycles each priced-but-not-natively-built op (variant) carries on the critical path
    zero = {}
    for (k, v) in [(k, v) for k, v in BUILD_EVIDENCE_KEYS(acc)]:
        def gz(r, dyn, L, k=k, v=v):
            c = cf(r, dyn, L)
            hit = f"{r.unit}.{r.op}" == k and (v is None or variant_of(r) == v)
            return (0.0 if hit else c[0]), c[1], c[2]
        zero[f"{k}|{v}"] = round(S2 - T.schedule(recs, DT.POS, "S2", cost_fn=gz)["total_cycles"], 1)
    from hgi_sim.records import encode_program
    return dict(S2_cycles=round(S2, 1), S2_tok_s=round(CLK / S2, 1), target_tok_s=DS_TARGET,
                image_bytes=len(encode_program(recs)),
                target_cycles=round(CLK / DS_TARGET, 1), price_scale_to_target=round(scale_to_target, 4),
                per_unit_S2=per_unit, ops=rows, critical_weight_if_zero=zero, program=str(PROG.relative_to(ROOT)), run=str(RUN.relative_to(ROOT)))


def qwen_budget():
    from hgi_sim import qwen_compiler as QC
    cfg = json.loads((ROOT / "compiler/models/qwen3-8b/config.json").read_text())
    recs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg["num_hidden_layers"])
    acc = collections.defaultdict(lambda: dict(n=0, cyc=0.0, items=0, what="", var=collections.Counter(),
                                               varn=collections.Counter()))

    def rec_cf(r, dyn, L):
        c = T.cost(r, dyn, L)
        a = acc[f"{r.unit}.{r.op}"]
        a["var"][variant_of(r)] += c[0]
        a["varn"][variant_of(r)] += 1
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
        st_q = status_of(ratio, grade)
        if st_q != "QUALIFIED" and (sched_with(k, BOUND_SLOWDOWN) - S2) / S2 < BOUND_RATE and build_status(k, None)[0] == "BUILT":
            st_q = "QUALIFIED_BY_BOUND"
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
                         measured_ratio=None if grade == "hand_entered" else ratio,
                         claimed_ratio_unmeasured=ratio if grade == "hand_entered" else None,
                         measured_grade=grade, measured_src=m.get("src"),
                         status=st_q, impact_cycles_per_token=round(impact, 1),
                         impact_tok_s=round(CLK / (S2 + impact) - CLK / S2, 1) if impact else 0.0,
                         owner=OWNERS.get(k, "hgi-1010"), elements=ELEMENTS.get(k, []),
                         variants={v: dict(records=a["varn"][v], price_cycles_per_token=round(c_, 1)) for v, c_ in a["var"].items()}))
    zero = {}
    for (k, v) in BUILD_EVIDENCE_KEYS(acc):
        def gz(r, dyn, L, k=k, v=v):
            c = T.cost(r, dyn, L)
            hit = f"{r.unit}.{r.op}" == k and (v is None or variant_of(r) == v)
            return (0.0 if hit else c[0]), c[1], c[2]
        zero[f"{k}|{v}"] = round(S2 - T.schedule(recs, 8191, "S2", cost_fn=gz)["total_cycles"], 1)
    return dict(S2_cycles=round(S2, 1), S2_tok_s=round(CLK / S2, 1), target_tok_s=QWEN_TARGET, critical_weight_if_zero=zero,
                price_scale_to_target=round(sc, 4), ops=rows,
                note="Qwen on HBM is deprioritised (runs exactly; TOKEN_SAVE 10-10); ratios are the audit's Qwen-shape "
                     "measurements")


def _rom_measured(grade):
    """token-path node grades that ARE RTL measurements at production shape: 'measured*', and 'apportioned' (an op window
    cut from a measured whole-layer RTL trace, e.g. qwen_plain_ar_stream4 RT_OPTRACE: the window's cycles are measured, only
    its attribution to an op is by trace position).  'priced' / 'modelled' are not."""
    return grade.startswith("measured") or grade == "apportioned"


# BOUND RULE (main 10-11): an op / class whose price is so small that even a 10x slowdown moves the token rate by < 1 %
# is QUALIFIED_BY_BOUND (no throughput bench needed); it must still be natively built (the build gate).  HBM ops: S2
# re-scheduled with the op at 10x its price; ROM classes: 9 x the class's critical cycles / token cycles.
BOUND_SLOWDOWN, BOUND_RATE = 10.0, 0.01


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
        if not _rom_measured(n["src"]["grade"]) and n["cycles"] > 0:
            c["unmeasured"].append(n["id"])
    cls_el = {c["id"]: c["elements"] for c in d["classes"]}
    rows = []
    for k, c in sorted(by.items(), key=lambda kv: -kv[1]["cycles"]):
        unm = sum(v for g, v in c["grades"].items() if not _rom_measured(g))
        allc = sum(c["grades"].values())
        # node prices are measured RTL unit cycles at production shape: a class qualifies when >= 95 % of its cycles
        # are measured; its few modelled nodes are listed as their own unbenched gaps (unmeasured_nodes)
        st = "QUALIFIED" if allc and unm / allc <= 0.05 else "UNQUALIFIED_NO_BENCH"
        if st != "QUALIFIED" and (BOUND_SLOWDOWN - 1) * c["cycles"] / tot < BOUND_RATE:
            st = "QUALIFIED_BY_BOUND"
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
    rom = {"qwen_rom": rom_budget("qwen_rom"), "ds_rom": rom_budget("ds_rom"), "ds_rom_mtp": rom_budget("ds_rom_mtp")}
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
    order = {"UNQUALIFIED": 0, "UNQUALIFIED_NO_BENCH": 1, "QUALIFIED_BY_BOUND": 2, "QUALIFIED": 3}
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
        put(e, "DS AR 1M (HBM)", "CP.FETCH", "UNQUALIFIED_NO_BENCH", None, OWNERS["CP.FETCH"],
            "HAND-ENTERED (unmeasured): budget_audit hbm_ds_cp_fetch claims 0.867 B/cyc needed vs 0.308 designed (2.8x); no committed CP-fetch bench record")
    for e in ELEMENTS["VM.PORTS"]:
        put(e, "DS AR 1M (HBM)", "VM.PORTS", "UNQUALIFIED_NO_BENCH", None, "hgi-1010/b (wide VM lanes)",
            "no production-shape VM lane-group bench against the client budget yet")
    for e in ELEMENTS["MTP.VERIFY"]:
        put(e, "DS MTP (HBM)", "MTP.VERIFY", "UNQUALIFIED_NO_BENCH", None, "hgi-1010/h + bf-mtp-1010",
            "hgi-1010.log 20:22 h: L0 verify 5 cols ~145k RTL vs 63.8k sim (interim); no native DS verify program")
    ws = next((x for x in dc if x["id"] == "hbm_qwen_weight_stream"), None)
    for e in ELEMENTS["SVC.STREAM"]:
        put(e, "Qwen AR 8K (HBM)", "SVC.STREAM", "UNQUALIFIED_NO_BENCH", None, "hbm-phys-1010",
            "HAND-ENTERED (unmeasured): budget_audit hbm_qwen_weight_stream claims 0.775 needed vs 0.862 bench proxy; no committed svc stream bench record cited")
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
    # ---- ROM per-block entries the token-path classes miss (main 10-10 23:xx): explicit BF hierarchy + name rules
    bf = BF_HIER
    for e in ("ot_v41_bf_col", "ot_s81_bf_front"):
        el.pop(e, None)
        put(e, "ds_rom", "BF hier_compact (field)", bf["status"], bf["ratio"], "bf-hier-1011", bf["src"])
        el[e]["bf_budget"] = bf
    cls_status = {(k, c["cls"]): c["status"] for k, v in rom.items() for c in v["classes"]}
    rom_rules = []
    for rx, model, cls, st, ratio, why in ROM_RULES:
        rom_rules.append(dict(pattern=rx, model=model, cls=cls, status=st, ratio=ratio, why=why))
    rom_cov = {}
    for e in ROM_BLOCKS:
        if e in el:
            continue
        for rr in rom_rules:
            if re.match(rr["pattern"], e):
                st = rr["status"] or cls_status.get((rr["model"], rr["cls"]), "UNQUALIFIED_NO_BENCH")
                put(e, rr["model"], "class:" + rr["cls"], st, rr["ratio"], rr["why"].split(":")[0] if ":" in rr["why"] else "-",
                    "name rule " + rr["pattern"] + ": " + rr["why"])
                rom_cov[e] = rr["pattern"]
                break
        else:
            put(e, "rom", "unmapped", "UNQUALIFIED_NO_BENCH", None, "-", "no token-path class and no name rule")
            rom_cov[e] = None
    # ---- provenance (main 10-10): every ratio must come from a committed bench record (path + commit)
    hand = []
    for model, part, table in (("DS", ds, MEASURED), ("Qwen", qw, MEASURED_QWEN)):
        for r in part["ops"]:
            m = table.get(r["op"], {})
            if r.get("measured_ratio") is None and not r.get("claimed_ratio_unmeasured"):
                continue
            path = (m.get("src") or "").split(" ")[0]
            c = prov(path)
            r["measured_record"] = dict(path=path, commit=c)
            if m.get("grade") == "hand_entered" or c is None:
                hand.append(dict(model=model, op=r["op"], claimed_ratio=r.get("measured_ratio") or r.get("claimed_ratio_unmeasured"),
                                 src=m.get("src"), owner=r.get("owner"), why="not a committed bench record of this op at this shape"))
    for e, v in el.items():
        for o in v["ops"]:
            if "HAND-ENTERED" in str(o.get("src")):
                hand.append(dict(model=o["model"], op=o["op"], element=e, claimed_ratio=None, src=o["src"], owner=o["owner"],
                                 why="audit-derived claim"))
    hand.append(dict(model="qwen_rom", op="KV die (name rule)", claimed_ratio=1.124, src="removed hand rule (superseded audit model)",
                     owner="qwen-1010/b", why="replaced by the measured KV-die record (pending)"))
    # ---- bench II (automated): the cycles / items line of every element's passing exact bench (closure-loop job state)
    bii = bench_ii()
    for e, b in bii.items():
        cur = el.get(e)
        if b["ii"] is not None and b["ii"] <= QUAL and not b["stalled"] and (cur is None or cur["status"] == "UNQUALIFIED_NO_BENCH"):
            el.pop(e, None)
            put(e, b["target"] or "rom", "bench II (" + b["item"] + ")", "QUALIFIED", round(b["ii"], 3), b["owner"],
                f"closure job {b['job']} @ {b['commit']}: {b['line'][:140]} (fixed-pipeline full-rate rule: <= 1.10 cycles an item)")
        elif cur is not None:
            cur["bench_ii"] = b
        else:
            put(e, b["target"] or "rom", "bench II (" + (b["item"] or "no items") + ")", "UNQUALIFIED_NO_BENCH", None, b["owner"],
                f"closure job {b['job']}: {b['line'][:140]} (II {b['ii']} > 1.10 or stalled stimulus: budget not mapped)")
            el[e]["bench_ii"] = b
    # ---- build gate: priced ops (per variant) with their native-RTL evidence
    RATES = {"DS": ["DS AR fixed-RTL 2,121.8 tok/s (results/arch/hgi_sim_20261010/ds_rates_g25.json AR.fixed_rtl)",
                    "DS MTP fixed-RTL 3,640.3 tok/s (ds_rates_g25.json MTP.fixed_rtl)",
                    "DS AR table 2,208.1 (budget_audit targets / token_path hbm_gen_ds)",
                    f"this budget's DS S2 {ds['S2_tok_s']} tok/s"],
             "Qwen": ["Qwen AR 953.8 tok/s (results/arch/hgi_sim_20261009/qwen_timing_P8191_v10.json S2)",
                      "Qwen DFlash b16 1,791.8 tok/s (dflash_timing.json)", f"this budget's Qwen S2 {qw['S2_tok_s']} tok/s"]}
    gate = []
    for model, part in (("DS", ds), ("Qwen", qw)):
        S2_ = part["S2_cycles"]
        for r in part["ops"]:
            for v, vv in (r.get("variants") or {None: {}}).items():
                vkey = None if v in (None, "None") else v
                st, ev = build_status(r["op"], vkey)
                w = part["critical_weight_if_zero"].get(f"{r['op']}|{vkey}")
                gate.append(dict(model=model, op=r["op"], variant=vkey, status=st, evidence=ev,
                                 records_per_token=vv.get("records", r["records_per_token"]),
                                 price_cycles_per_token=vv.get("price_cycles_per_token", r["price_cycles_per_token"]),
                                 critical_cycles_if_zero=w,
                                 rate_if_op_free_tok_s=round(CLK / (S2_ - w), 1) if w else None,
                                 inflates=RATES[model] if st != "BUILT" else []))
    rec = dict(schema="opentallas.throughput_budget.v1",
               bound_rule=dict(slowdown=BOUND_SLOWDOWN, max_rate_change=BOUND_RATE,
                               rule="QUALIFIED_BY_BOUND: a natively built op / class whose 10x slowdown moves the token rate by < 1 % "
                                    "(HBM: S2 re-scheduled with the op at 10x; ROM: 9 x class critical cycles / token cycles)"),
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
               build_gate=dict(rule="every op the simulator prices needs a committed bench that executes it natively in RTL "
                                    "(no stub, no behavioural model, no unsupported status); else PRICED-NOT-BUILT",
                               rows=gate, priced_not_built=[g for g in gate if g["status"] != "BUILT"]),
               hand_entered=hand, bench_ii=bii,
               bf_hier=BF_HIER, rom_block_rules=rom_rules, rom_block_coverage=rom_cov,
               hbm_datactl_rows=dc, svc_endpoint_budget_ds=svc, qwen_hbm=qw, rom=rom, rom_audit_rows=rom_audit,
               elements=dict(sorted(el.items())))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    for x in ranking:
        print(x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
