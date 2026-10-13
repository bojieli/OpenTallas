#!/usr/bin/env python3
"""Fill the accepted-cost ledger with the units measured over 1.10x on 2026-10-13 (all rows 'proposed').

    python3 tools/throughput/accepted_cost_fill_1013.py [--ledger PATH] [--jobs N]

ROM designs first (token-path DAG), then the HBM die (S2 re-schedules; the DS program takes about a minute per op, run
in parallel).  Rows that measure the same composition op share a group.  Nothing here marks a row accepted.
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import accepted_cost as AC  # noqa: E402

DATE = "2026-10-13"
HO = "~/claude-takeover-20261007/HANDOFF.md"
B = "results/arch/throughput_budget_20261010/budget.json"
U = "results/rtl/hgi_unit_tput_20261010/"

ROM = [
    dict(design="s81", unit="SU.HC_POST (ot_dsrom_su_hcpost, current production POST)", group="SU.HC_POST",
         kw=dict(match=r"hc_post$", price=112.9, measured=287.0),
         evidence="results/rtl/s81hc_throughput_20261013/baseline.json", grade="committed_bench",
         note="twelve production POST jobs at 286-287 cycles against the immutable 112.9 (source 3c62573d5); 80 runs a "
              "token (attn + ffn x 40 layers), all on the critical path; in MTP the slowest verify stage holds two, paid "
              "again at each of the 5 wave positions; the 6 draft-block hc_post nodes (641.3, another vehicle) are not "
              "touched.  CURRENT BASELINE: to be replaced by the POST express measurement (post_express_spec.json)."),
    dict(design="s81", unit="MTP p2.core_transaction (ot_mtp_p2_prefix_path)", group="MTP.p2.core_transaction",
         kw=dict(match=r"^mc\.p2\.selected_path$", price=5467.0, measured=6092.0, node_delta=3 * (6092.0 - 5467.0)),
         evidence="results/rtl/dsrom_mtp_wave_bench_20261011/record.json", grade="committed_bench",
         note="wave bench charge p2.core_transaction 6,092 measured / 5,467 price; the step charges it three times "
              "(mtp.0-2 rank prefixes, node mc.p2.selected_path = 3 x (5,467 - 348)), on the critical path; MTP only"),
    dict(design="qwen_rom", unit="KV-end d2d credit class 6 (HCTL, 4 credits)", group="KV_END.class6",
         kw=dict(price=0.44, measured=0.40, words_per_token=0.0), rate=True,
         evidence="rtl/test/qwen_kv_die/tb_qkvd_d2d_pair.sv (SAT probe; figure in ~/claude-takeover-20261007/el1011-q-kvd.log 10-12 17:23, main c4a1f1403)",
         grade="interim_log",
         note="pop-flop (PQ) kv_end: the 4-credit class 6 is round-trip bound at 0.40 words/cycle, was 0.44 (ratio "
              "1.10, at the limit); class 6 is HCTL (qkd_host -> sequencer: START / CSR / STOP / status, host-driven, "
              "CONTRACT.md) and carries 0 words in a token step; the token classes (sbuf, 8+ credits) hold 1 "
              "word/cycle, so the measured attention layer step (1,814) does not move"),
]

# HBM die r25gq: (unit, group, op, price, measured, workloads or None, evidence, grade, note)
HBM = [
    ("SM.MATVEC [bench of record]", "SM.MATVEC", "SM.MATVEC", 115.9, round(115.9 * 27.202, 1), ["ds_ar"],
     U + "sm/report.json", "committed_bench",
     "bench of record 27.202x (tb_hgi_sm_tput, before x-reuse); not re-measured since 357764a5c"),
    ("SM.MATVEC [x-reuse, L0 1.95x / L1 1.73x]", "SM.MATVEC", "SM.MATVEC", 1.0, 1.95, None,
     HO + " line 198 (x-reuse main 357764a5c; no committed bench record)", "interim_log",
     "the L0 figure applied to every SM.MATVEC record of both programs (price and measured are the ratio)"),
    ("SM.MATVEC held xload [legacy FW8 L1]", "SM.MATVEC", "SM.MATVEC", 3689.1, 5016.0, None,
     "~/claude-takeover-20261007/CLAUDE_RESUME_20261013.md line 47 (hbm_smmv held xload)", "interim_log",
     "5,016 cycles against the immutable 3,689.1 record price (1.36x), applied to every SM.MATVEC record"),
    ("SM.MATVEC VM8 service [P8 FP8 xload, always-ready]", "SM.MATVEC", "SM.MATVEC", 2111.0, 2843.0, None,
     "~/claude-takeover-20261007/el1011-hbm-smmv-b.log line 190; CLAUDE_RESUME_20261013.md line 20", "interim_log",
     "four-seat strict credit injects bubbles: service 2,843 against the 2,111 BASELINE measurement (not a price: "
     "1.347x is the regression, the ratio to price is not measured); applied to every SM.MATVEC record as an upper "
     "bound of the xload phase's share"),
    ("FUSED.QDQ_FP8 quant_wide_h cluster [serial records]", "FUSED.QDQ_FP8", "FUSED.QDQ_FP8", 168.0, 751.0, ["ds_ar"],
     "~/claude-takeover-20261007/el1012-hbm-fq-cx.log line 1; " + HO + " line 198", "interim_log",
     "751 / 168 = 4.47x is a serial-transaction measurement (bench waits done per record); the overlap prototype "
     "0edd4cbcf reaches 184 / 168 = 1.095"),
    ("FUSED.QDQ_FP8 [bench of record, WIDE]", "FUSED.QDQ_FP8", "FUSED.QDQ_FP8", 24.0, round(24.0 * 2.74, 1), ["ds_ar"],
     U + "qdq_wide/report.json", "committed_bench",
     "budget.json carries this op as ACCEPTED at 2.74x (tput-gate-1010); this row puts that acceptance under the "
     "10-13 rule"),
    ("SFU.GLU [latest 1.41x]", "SFU.GLU", "SFU.GLU", 120.0, round(120.0 * 1.41, 1), ["qwen_ar"],
     HO + " line 198", "interim_log", "one SFU record a layer, Qwen program only (the DS program issues no SFU.GLU)"),
    ("SFU.GLU [bench of record, ot_hgi_sfu_record]", "SFU.GLU", "SFU.GLU", 120.0, round(120.0 * 1.933, 1), ["qwen_ar"],
     "results/rtl/tput_map_1011/qwen_sfu/record.json", "committed_bench",
     "compute 125 vs 120; the rest is the unpriced serial span + stage + drain around one record a layer"),
    ("SU.VOP [latest 1.249x]", "SU.VOP", "SU.VOP", 1.0, 1.249, None, HO + " line 198", "interim_log",
     "applied to every SU.VOP record of both programs (the DS bench of record is 1.067, qualified)"),
    ("SU.VOP [Qwen bench of record, hfd_su_result_ingress]", "SU.VOP", "SU.VOP", 1548.0, round(1548.0 * 1.946, 1),
     ["qwen_ar"], "results/rtl/tput_map_1011/qwen_su/record.json", "committed_bench",
     "compute 1,327 is under the 1,548 price; the 1.95x is stage + drain + span the 3-slot pipeline does not hide"),
    ("HC.HC_MIX_POST", "HC.HC_MIX_POST", "HC.HC_MIX_POST", 540.0, round(540.0 * 1.282, 1), ["ds_ar"],
     U + "hc/ds_L0_tput/report.json", "committed_bench",
     "S2 overlaps this op: it is off the token's critical path (the scalar c4 POST since measured 540 / 540 on main "
     "cb565793e; the registry still maps the 1.282 vehicle)"),
    ("IDX.INDEX", "IDX.INDEX", "IDX.INDEX", 939.2, round(939.2 * 8.603, 1), ["ds_ar"],
     U + "idx_index/report.json", "committed_bench", "old IXW0 adapter; B2 IXW1 source 0d8f55c19 is being measured"),
    ("IDX.TOPK", "IDX.TOPK", "IDX.TOPK", 283.0, round(283.0 * 4.286, 1), ["ds_ar"],
     U + "idx/ds_L0_tput/report.json", "committed_bench", "TOPKW=1 heap (9473077de)"),
]

_SCHED = {}


def _hbm_one(args):
    model, op, ratio, base = args
    if model not in _SCHED:
        _SCHED[model] = AC.hbm_schedule(model)
    run, count = _SCHED[model]
    if op is None:
        return run()
    return AC.hbm_loss(run, count, op, ratio, base)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", default=str(AC.LEDGER))
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    led = AC.load_ledger(a.ledger)
    for r in ROM:
        per = AC.compute(r["design"], **r["kw"])
        rate = r.get("rate", False)
        AC.propose(led, AC.make_row(r["design"], r["unit"], r["kw"]["price"], r["kw"]["measured"], per, r["evidence"],
                                    r["grade"], r["note"], rate, DATE, "words/cycle" if rate else "cycles", r["group"]))
    models = AC.DESIGNS["r25gq"]["workloads"]
    with ProcessPoolExecutor(a.jobs) as ex:
        base = dict(zip(models.values(), ex.map(_hbm_one, [(m, None, None, None) for m in models.values()])))
        jobs = [(i, wl, m) for i, h in enumerate(HBM) for wl, m in models.items() if h[5] is None or wl in h[5]]
        res = list(ex.map(_hbm_one, [(m, HBM[i][2], HBM[i][4] / HBM[i][3], base[m]) for i, wl, m in jobs]))
    per = [dict() for _ in HBM]
    for (i, wl, m), r in zip(jobs, res):
        if r:
            per[i][wl] = r
    for h, p in zip(HBM, per):
        AC.propose(led, AC.make_row("r25gq", h[0], h[3], h[4], p, h[6], h[7], h[8], False, DATE, "cycles", h[1]))
    AC.save_ledger(led, a.ledger)
    print(AC.table(led))


if __name__ == "__main__":
    main()
