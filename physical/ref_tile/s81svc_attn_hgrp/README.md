# s81svc_attn_hgrp -- S81 svc_rs attention head group (SVC3, LEAD2-S81, 10-19)

Top `ot_hdc_v41x_attn_hgrp_s81` (rtl/hdc/v41x/ot_hdc_v41x_attn_hgrp_s81.sv) = `ot_hdc_v41x_attn_hgrp_s` at the S81
engine parameters H16 HG4 TD32 NBANK5 BW3 PWORDS2 FPL4 FML6 F12 1 PCOLP 1, parameter-free. 16 per
`dsdv_svc_rs_attw` engine (4 tiles x 4 groups; `ot_hdc_v41x_attn_tile_s` with `-DOT_ATTN_HGRP_HARD`).

Why: the attw synth stall is the engine's 4 x `ot_hdc_v41x_attn_tile_l` (933k pre-cells each), and that tile_l is the
`SVCQ_ENG_FG3` simulation build (FPL 3 / FML 3), not the 833 ps build. The production engine (no FG3: FPL 4 f12 adds,
FML 6 split product, TILE_S 1) is tile_s = 4 hardenable head groups + wiring. No closed view of tile_l / tile_s /
an S81-parameter head group exists (the HBM `ot_attn_hgrp_m6h1` is one head at TD 64, SS sign-off, selected=false).

Bench: `tools/s81_dv/svc_rs/hgrp_bench.sh` (Verilator 5.050): rtl/test/tb_hdc_v41x_attn_tile_s_lockstep.sv at the S81
parameters, tile_s built from 4 x this element vs tile_l, every output every cycle, 20k cycles; mutants 1 (gid ignored)
and 2 (head-0 fault dropped) must FAIL. Added cycles: 0 (same cycles as hgrp_s / tile_l FML 6).

## Safe-design checklist (owner 10-19)
1. Pins: PASS (source-registered). Every input lands in a flop (R0 r_iv/r_ibank/r_ib; per-head kept kreg copies of
   ld_*; hh/gsel from gid), every output is a flop (ov/oy/oflt); recipe pin_regs off with that reason (a second stage
   would be unpriced). Reset lands in 2 stages at the face (reset_landing).
2. Reach: PASS by outline 388.8 x 388.8 um (< 405 um side; first gate measures util and wire_reach).
3. Fanout: PASS by construction: the 1,024-bit load word has one kept copy per head (ot_hdc_v41x_kreg, kept hierarchy);
   R0 issue registers drive 4 heads x 1 multiplier column. CHECK at gate: kreg is parameterised ($paramod name) ->
   verify 4 copies survive synthesis (yosys-keep-parameterised-modules-1018).
4. Depth: PASS (design): FPL 4 = ot_hdc_fp32_add_f12_l4 (1.2 GHz SS unit), FML 6 split 8x4 product, dequantiser split
   across D1; gate --cts reports the worst classes.
5. Storage: WAIVED with reason: stationary operands 5 banks x 16 b per multiplier (2,560 b / head) are read by 32
   multipliers EVERY cycle with 8 different chunk-position bank selects -> a per-multiplier 5-entry operand register,
   not a runtime-indexed array an SRAM port could serve; skew lines (<= 24 x 18 b per element) are fixed systolic delays.
   If FF hold misses concentrate on skew chains -> ring-buffer variant (parallel kit), not a squeeze.
6. Floorplan: PASS: no macros; outline square (1:1); ld_w 1,024 pins on W (2.6 pins/um), ib 576 on S, ld_wp+ctl on N,
   oy on E; util from the first gate's synthesis area (target 40-60 %; resize the outline from it).
7. Clock: local TritonCTS (leaf); pin-flop spread <= 80 ps TT+FF checked by the gate; io_hold_margin 0.03.
8. Schedule: PASS: static (no credits / ready); zero added cycles.
