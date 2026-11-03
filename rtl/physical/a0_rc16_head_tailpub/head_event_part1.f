// Canonical native Qwen HEAD event (stage37): selected PART1 publisher = option A, the explicit valid-row
// publisher (owner decision 2026-11-02 17:55).  In the event's source list this file REPLACES
//   rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv
// (kept byte-identical), and the define makes TAILPUB = 1 the default of every ot_qwen_w12_matvec_part instance
// (all NK/NL A0 tiles); the publisher masks valid only on ops of the HEAD lease (wbase 18432..20031, split 9,
// mmode 0, ROM-sourced, W-aligned nout) and publishes raw on every other op.  The event's own top-level enable
// (TOK-QW-3, held / default off) is not changed by this selection.
+define+OT_QWEN_HEAD_TAILPUB
rtl/physical/a0_rc16_head_tailpub/ot_qwen_w12_matvec_land32.sv
