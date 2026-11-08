QC calendar FIFO2 plan event (DIE-QC-93, 2026-11-08). R5 READY plan event for the FIFO2 form.

Change: only partition type tt_ctlm.
  - It drops 4 hard cores u_bound.u_core.u_gi.u_cal.g_fifo[0..3].u_fifo (ot_sram_1r1w_64x512_m1_r2c2).
  - asbuilt prefer: qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv -> its _fifo2.sv alternate, which changes only the 4 master tokens.
  - asbuilt files: + rtl/physical/ot_qc_cal_fifo2_512.sv.
Cycles: data 0, pin 0, boot 0. Ports unchanged. No other type changes.

Guard: base_guards.json holds the sha256 of the tt_ctlm type, a00b5c9e74a0. That value is the same in plan_qc53v4s, v4u and v4x_fws.
The prefer entry is literal-guarded.

Usage:
  python3 -I apply_event.py --plan <plan.json> --out-plan <out.json> [--asbuilt <asbuilt.json> --out-asbuilt <out.json>]...
  The patched asbuilt must stay in the same directory depth as its source, because "base" is a relative path.

Dry run (11-08):
  - Applied to plan_qc53v4x_fws: only tt_ctlm changes.
  - The resulting tt_ctlm equals the PLACE-reviewed private FIFO2 kit dq92/fifo2_gen2/fifo2_form_a/plan_fifo2.json, except for the note.
  - bind kit-rtl: see event_report.json.

Physical (private form, intel2 dq92/fifo2_gen2/fifo2_form_a/gen/tt_ctlm):
  - PLACE_RC 0, 327,333 cells, density p99 0.38 / max 0.54.
  - reg_fanout PASS: 45,571 regs, all <= 8 loads.
  - 15 macros kept.

Helper proof: tools/qwen_dv/cal_fifo2_0222 run1 PASS. Against the old macro: 792x512-bit reads, 0 differences. The mutants are detected.

EQ: the kit LEC is UNPROVEN. This is a tool class, not a design result:
  - tools/die_plan/lec.py escaped_instance_blocks uses ESC_DOTTED, which accepts only plain identifiers per segment.
  - So '\u_gi.u_cal.g_fifo[0].u_fifo ' (a segment with an index) is not moved into generate blocks.
  - yosys-slang --keep-hierarchy then derives the module name '...\u_gi.u_cal.g_fifo[0].u_fifo ', with a space, which RTLIL rejects.
  - It appears now because the helper is a source-defined module; the old SRAM was a black box, which the rewriter skips.
  - Adoption stays EQ-gated: a kit LEC EQUIVALENT is required after the flow fix.
