#!/usr/bin/env python3
"""Compose tok/s from the joint sweeps: token' = token_of_record + dSched / (1 + land%) (toksim_hbm_compose_1019 /
hbm_rate7 tok_from_sched order; DS land -1.13 %, Qwen -0.07 %; 1.2 GHz edge).  Writes result.json."""
import json
from pathlib import Path
H = Path(__file__).resolve().parent
CLK = 1.2e9
LAND = {"ds": -1.13, "qwen": -0.07}
# rows of record: (sweep base, label, DS token cycles of record, DS tok/s, Qwen token cycles, Qwen tok/s, source)
ROWS = [
    ("h9b", "RELEASE of record: bound H9b/h9c controller (meas_h9b, COORD 23:24 'HBM ships with h9c', DS ~1,000)",
     1207635.2, 993.7, 2232996.1, 537.4, "results/token_pass/measured_hbm_1019/cycles.json scenarios.meas_h9b"),
    ("r7xl", "NEXT-RELEASE accepted (MC3c successor + x-reuse, HBM-RATE7 m_xl_i8; owner-accepted ~1,341 -> 1,331.6 after head)",
     901166.7, 1331.6, 1198142.9, 1001.5, "results/rtl/hbm_rate7_1020/census/tok.txt m_xl_i8"),
    ("r7all", "NEXT-RELEASE all levers (HBM-RATE7 m_all)", 901166.7, 1331.6, 1186614.8, 1011.3,
     "results/rtl/hbm_rate7_1020/census/tok.txt m_all"),
    ("r7base", "HBM-RATE7 m_base (successor, no x-reuse)", 1050955.4, 1141.8, 1199158.6, 1000.7,
     "results/rtl/hbm_rate7_1020/census/tok.txt m_base"),
    ("i8su", "TOKEN-LEAD 10-20 combined (successor p80, SU.VOP measured, no head repair)", CLK / 1109.7, 1109.7, CLK / 372.2, 372.2,
     "results/token_pass/measured_hbm_1019/README.md combined_1020 (cycles = 1.2e9 / tok/s)"),
    ("rel98", "rel98 (successor p80, MB attention, SU.VOP model)", 1038612.0, 1155.4, 1196507.8, 1002.9,
     "results/token_pass/measured_hbm_1019/cycles.json scenarios.rel98"),
]
out = dict(schema="opentallas.hbm_price_qdq54_hc17.v1", lane="STEWARD-TOKb-HBMPRICE", date="2026-10-21",
           costs=dict(qdq=dict(what="hb_quant_NW ot_hgi_qdq_host_split_r3 + ctl_r4s read latency RL 7 -> 54",
                               per_record_edges=47, records_per_token_ds=40, records_per_token_qwen=0,
                               measured_record_before=58, record_after=105),
                      hc_tail=dict(what="HC tail k4 TSDIV 17 TTPIPE 1 TSKP 2 (L 496 -> 989) + hardened tail child TAILC TE 2: root emit TE 2 -> 495",
                                   per_record_edges=495, records_per_token_ds=80, records_per_token_qwen=0,
                                   measured_record_before=1055, record_after=1550)),
           occupancy_edges_added_per_ds_token=40 * 47 + 80 * 495, rows=[])
for key, label, dsc, dst, qc, qt, src in ROWS:
    sw = json.loads((H / "sweeps" / f"joint_{key}.json").read_text())
    b, p = sw["0+0"], sw["495+47"]
    dds = p["ds_schedule_total"] - b["ds_schedule_total"]
    dq = p["qwen_schedule_total"] - b["qwen_schedule_total"]
    ddt = dds / (1 + LAND["ds"] / 100)
    dqt = dq / (1 + LAND["qwen"] / 100)
    out["rows"].append(dict(base=key, label=label, source=src,
                            ds_sched_base=b["ds_schedule_total"], ds_sched_priced=p["ds_schedule_total"],
                            ds_sched_delta=round(dds, 1), ds_token_cycles_added=round(ddt, 1),
                            ds_crit_records_before=b["crit"], ds_crit_records_after=p["crit"],
                            ds_tok_s_old=dst, ds_tok_s_new=round(CLK / (dsc + ddt), 1),
                            qwen_sched_delta=round(dq, 1), qwen_tok_s_old=qt, qwen_tok_s_new=round(CLK / (qc + dqt), 1),
                            users="HBM single-user (1 x tok/s); MTP not priced (HBM MTP = next release, deferred)"))
(H / "result.json").write_text(json.dumps(out, indent=1) + "\n")
for r in out["rows"]:
    print(f"{r['base']:7s} DS {r['ds_tok_s_old']} -> {r['ds_tok_s_new']} (+{r['ds_token_cycles_added']} cyc)  Qwen {r['qwen_tok_s_old']} -> {r['qwen_tok_s_new']}")
