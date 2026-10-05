#!/usr/bin/env python3
"""Build closure.json of the DS HBM SM family (hbm-fmax-sm) from the committed route / corner STA / gate records."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
REC = D / "records"
ROOT = D.parents[3]


def cs(lab):
    p = REC / lab / "corner_sta.json"
    if not p.is_file():
        return None
    c = json.loads(p.read_text())
    out = dict(record=str(p.relative_to(ROOT)), period_ns=0.833, ss_r2r_ps=c["setup_ss"]["worst_reg_to_reg_slack_ps"],
               ss_worst_ps=c["setup_ss"]["worst_slack_ps"], ss_input_to_reg_ps=c["setup_ss"]["worst_input_to_reg_slack_ps"],
               ss_output_ps=c["setup_ss"]["worst_output_port_slack_ps"], ff_hold_ps=c["hold_ff"]["worst_slack_ps"],
               closes_signoff=c["closes_signoff"])
    ph = REC / lab / "physical.json"
    if ph.is_file():
        d = json.loads(ph.read_text())["design"]
        out.update(cell_area_um2=d.get("area_um2"), cells=d.get("cells"), physical=str(ph.relative_to(ROOT)))
    return out


def gate(name):
    p = REC / f"gate_{name}.json"
    if not p.is_file():
        return None
    g = json.loads(p.read_text())
    return dict(record=str(p.relative_to(ROOT)), status=g["status"], cases=g["cases"],
                mismatching_cases=g["mismatching_cases"], delta_done=g["delta_done_set"],
                delta_first=g["delta_first_set"])


shapes = json.loads((REC / "gate_shapes.json").read_text()) if (REC / "gate_shapes.json").is_file() else None
per_op = []
if shapes:
    for c in shapes["results"]:
        per_op.append(dict(shape=c["case"], ops=len(c["ops"]), original_cycles_start_to_done=c["cycles_start_to_done"][0],
                           successor_cycles_start_to_done=c["cycles_start_to_done"][1],
                           drain_last_line_to_last_result=c["drain"], original_reproduces_baseline_record=
                           c["original_reproduces_record"], exact=[c["exact_original"], c["exact_successor"]]))
dd = sorted({p["drain_last_line_to_last_result"][1] - p["drain_last_line_to_last_result"][0] for p in per_op}) if per_op else None
# per-token composition (lines_drain mode of tools/dshbm_baseline_measure.py): sm = sum over op groups of
# (lines + drain) / f, barrier = groups x 78 cycles / f; the baseline record gives sm 70.12 us, barrier 22.29 us at
# 1.2 GHz -> 343 op groups (22.29e-6 x 1.2e9 / 78).  Every group's drain grows by the measured drain delta; the
# barrier crossing by 2 x PIO (arrive out, release in; measured released_after_done).
F = 1.2e9
groups = round(22.29e-6 * F / 78)
d_drain = dd[0] if dd and len(dd) == 1 else None
d_bar = 4
token = None
if d_drain is not None:
    token = dict(op_groups_per_token=groups, drain_cycles_added_per_group=d_drain, barrier_cycles_added_per_group=d_bar,
                 sm_us_1p2GHz=dict(baseline_model_clock=70.12, successor=round(70.12 + groups * d_drain / F * 1e6, 2),
                                   as_built_0p59GHz=142.69),
                 barrier_us_1p2GHz=dict(baseline=22.29, successor=round(22.29 + groups * d_bar / F * 1e6, 2),
                                        as_built_0p59GHz=45.37),
                 sm_plus_barrier_us=dict(as_built_0p59GHz=round(142.69 + 45.37, 2),
                                         successor_1p2GHz=round(70.12 + 22.29 + groups * (d_drain + d_bar) / F * 1e6, 2)),
                 basis="lines_drain composition of results/rtl/dshbm_baseline_measured_20261004/measured.json with "
                       "the successor's measured drain at every measured op shape (gate_shapes.json); SM cycles are "
                       "shape-determined (data-independent: the issue, ring and pipelines never branch on operand "
                       "values), so the per-op cycle table at the measured shapes is the composition input")

rows = [
    dict(module="ot_hbm_accel_sm_v (ENABLE=1)", file="rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv",
         params=dict(ENABLE=1, NC=8, RMAX=4096, SUB=4, LBS=2, LSB=16, IL=8, LEV=4, XD=128, TCK=1, DS=3, DW=4, DG=3, PIO=2),
         on_token_path="yes: the DS HBM SM element (32 per die) that runs every matvec of the DS token "
                       "(results/rtl/dshbm_baseline_measured_20261004 sm term)",
         before=dict(evidence="results/rtl/risk_clock_loops_20261003/screens/hbm/bulkcopy_ds_833.json (as built 0.59 GHz: "
                              "ot_gpu_bulk_copy consume loop); ot_gpu_sm_v never routed at 0.833",
                     period_ns=1.695),
         after=cs("sm_r1"),
         false_path_io="no: IO constrained by the W13 die budget (inputs 300 ps internal, outputs 450 ps incl. "
                       "insertion; rtl/hbm_accel/sm/ot_hbm_accel_sm_v_die_budget.sdc)",
         fix=("successor element: closed issue/bulk copy; issue outputs registered (s1); leaf per (column, sub) with "
              "its own x-store macros (fragment re-laid out, per-bit write masks); keep_hierarchy replicated "
              "distribution (DS per-sub stages + per-half copy), gather (DG stages), registered boundary (PIO, "
              "credit channels for descriptor/request); combine-tree select by the op's registered format"),
         cycles_added=dict(per_op_drain=d_drain, per_op_start_to_done=shapes and shapes["delta_done_set"],
                           barrier_crossing=d_bar, issue_rate="unchanged (one line a cycle)"),
         exactness=dict(synthetic=gate("synth"), shapes=gate("shapes"), edges=gate("edges"))),
    dict(module="ot_hbm_accel_issue (ENABLE=1)", file="rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv", params=dict(ENABLE=1, IL=8, RMAX=4096, XDEPTH=128),
         on_token_path="yes (SM issue sequencer)",
         before=dict(evidence="results/rtl/hbm_clock_loops_20261004/routes/issue_ds_0833_r4/corner_sta.json",
                     period_ns=0.833, ss_r2r_ps=27.94, ss_worst_ps=-136.66, ff_hold_ps=8.4,
                     note="output ports -137 ps against a 20% output delay"),
         after=dict(note="proven in the SM context: outputs registered at s1 inside the element; see the element row",
                    **(cs("sm_r1") or {})),
         fix="adv/xa/control registered in the SM (s1); x read issued from s1", cycles_added=dict(per_op="+1 setup (HA3) + x read from s1 (in element total)")),
    dict(module="ot_hbm_accel_bulk_copy (ENABLE=1, RING_MACRO=1, LINE_BITS=1088)", file="rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv",
         on_token_path="yes (SM weight stream)", before=dict(evidence="results/rtl/hbm_clock_loops_20261004/bulk/closure_r12.json",
         period_ns=0.833, ss_worst_ps=13.51, ff_hold_ps=11.43, closes_signoff=True),
         after=dict(note="reused unchanged; its ports are registered inside the element (s1, credit channels, rsp pipe)",
                    **(cs("sm_r1") or {})), cycles_added=dict(per_op=0)),
    dict(module="ot_hbm_accel_tc16 (successor of ot_gpu_tc16 / ot_gpu_tc_col L16)", file="rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv",
         on_token_path="yes (BF16 column macro, 32 per SM)",
         before=dict(evidence="results/physical_abi3/asap7/gpu/w13_tc16_terminal_20261001T120346Z/receipt.json", period_ns=0.833,
                     ss_worst_ps=-31.06, ff_hold_ps=5.22, also=cs("tck_l1")),
         after=cs("tck2_u45"), false_path_io="yes: registered boundary (every input lands in a flop, every output leaves one)",
         fix="bubble gate moved off the multiplier's first stage (kill -> zero flag); 8x8 significand product cut as two 8x4 "
             "partial products summed by a kept prefix adder in stage 3 (biased exponents precomputed); LATENCY 5 kept",
         cycles_added=dict(per_op=0),
         exactness=dict(bench="rtl/test/tb_hbm_accel_bmul_equiv.sv (vs ot_hdc_bmul with the original gate)", vectors=2000000,
                        mismatches=0, element="gate_synth / gate_shapes / gate_edges")),
    dict(module="ot_hbm_accel_bd_col (successor of ot_gpu_bd_col; ot_hbm_accel_bterm2 of ot_v41_bterm2)", file="rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv",
         params=dict(M1=10), on_token_path="yes (FP8/FP4 block-dot column macro, 32 per SM)",
         before=dict(evidence="results/physical_abi3/asap7/gpu/w13_followup_20261001/terminal_snapshot/ot_gpu_bd_col/corners.json "
                              "(+14.3, all layers); as an M2-M6 leaf macro", also=cs("bdcol_l1")),
         after=cs("bdk10_l1"), false_path_io="yes: registered boundary",
         fix="FP4 E2M1->E4M3 decode in the P0 register (removes the fp4 flag fanout from P1); CSA cut 32->10 | 10->2",
         cycles_added=dict(per_op=0), exactness=dict(element="gate_synth / gate_shapes / gate_edges (FP4 and FP8 ops)")),
    dict(module="ot_gpu_stack (LEV 4, IL 8, TAGW 12, ALAT 7)", file="rtl/gpu/ot_gpu_stack.sv", on_token_path="yes (per-column reducer)",
         before=dict(evidence="screen r2r -126 ps (risk_clock_loops); TT route only"), after=dict(standalone=cs("stack_orig"),
         in_context="see element row (soft in the SM hub; inputs from ot_gpu_tree registers)"), fix="none needed", cycles_added=dict(per_op=0)),
    dict(module="ot_gpu_tree (N 4) / ot_gpu_fadd = ot_hdc_fp32_add_lat LAT7", file="rtl/gpu/ot_gpu_tree.sv",
         on_token_path="yes", before=dict(evidence="LAT7 standalone +40.1 ps; ABC re-ripple risk in context"),
         after=dict(in_context="see element row (tree inputs registered; ot_hdc_ksadd_k kept prefix adders)"), cycles_added=dict(per_op=0)),
    dict(module="ot_v41_bterm / ot_v41_bterm2 / ot_hdc_blockdot", on_token_path="yes (inside the block-dot column)",
         after=dict(note="covered by ot_hbm_accel_bd_col's routed sign-off (bterm2 successor inside)")),
    dict(module="ot_gpu_xstore", file="rtl/gpu/ot_gpu_xstore.sv",
         on_token_path="no for DS: ot_gpu_sm_v / the successor use per-leaf x-store macros; ot_gpu_xstore is Qwen's ot_gpu_sm_q only (off-path below)"),
    dict(module="ot_gpu_fmul / ot_hdc_fp32_mul_lat (row scale)", on_token_path="no for DS: the row-scale multiply exists only in ot_gpu_sm_q (Qwen, off-path)"),
    dict(module="ot_hbm_accel_sm_q / ot_gpu_sm_q (Qwen)", file="rtl/hbm_accel/epilogue/ot_hbm_accel_sm_q.sv",
         on_token_path="no: the measured Qwen HBM token (HA8, results/rtl/hbm_accel_ha8_20261004) runs the W12 ROM datapath; "
                       "its token_result.json source_sha256 lists no rtl/gpu/* and no ot_hbm_accel_sm_q (W12 owner: another agent)"),
]
pending = ["real-operand rerun of sm_real_ops (w19_sm_real_ops on the TP-96 executor's dump): the dump of the baseline "
           "was not preserved and the TP-96 golden executor is a CPU numpy model execution barred on every host "
           "(owner rules 2026-10-04); exactness is proven on seeded operands at every measured shape + FP edges, and SM "
           "cycles are shape-determined"]
out = dict(schema="opentallas.hbm_accel.fmax_closure.v1", family="sm", topic="hbm-fmax-sm",
           clock="0.833 ns, SS setup +60 ps, FF hold +25 ps (tools/w18/corner_sta.py)", rows=rows, per_op_cycles=per_op,
           per_token=token, unvalidated=pending)
(D / "closure.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps(dict(element=rows[0]["after"], token=token), indent=1))
