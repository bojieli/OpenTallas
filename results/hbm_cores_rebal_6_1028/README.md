# HBM-CORES-REBAL-6 (2026-10-28)

## side_rest _c20ek2s LEC NOT EQUIVALENT (1462 differ): diagnosis (no rebuild)
Kit intel2:/srv/opentallas-scratch2/claude/hbm-cores-rebal-2/kits/ot_hbm_su_static_pgslice_lg__side_rest_f426418b0b7b-_c20ek2s/lec.
- Reset port: rst_n, recognised (reset_ports gold/gate pi:rst_n[0]) -> NOT the hrst_n cause.
- u_div (y[31:0] + fault, 33 points): u_div a = 32'h3F800000, so d_zero = 0 and the zero flag is constant 0 through
  18 unreset stages (d_zero, e_zero, r_zero[0..13], f1_zero, f2_zero). Synthesis removes it (legal). lec.py can
  give an unreset constant a base case only within 4 reset + 8 release edges (hypotheses exist up to
  r_zero[1][1] = edge 12), and y observes f2_zero every cycle. = KV-KITS-9 cause 1. Fix: fdiv ZERO_RST (async reset
  of the zero chain to 0, opt-in) on side_rest u_div only.
- u_egs (466 g_dig[10..25].src_rem/src_root + f_sticky): gate u_egs and u_sq (same ot_hdc_fsqrt) keep identical bit
  sets; u_sq passes. In u_egs the gold-only rem_stage[0][34..61] hypothesis is eq gold g_dig[2].src_rem[0] (itself
  const 0) instead of const 0 (u_sq). Equality hypotheses block reload base cases -> 471 u_egs shift-in zero
  constants dropped -> 466 differ. A third cause (lec.py hypothesis form), not a design bug. Fix: lec.py
  eq_const_resolve (eq-to-const -> const, same base-case test as any constant).
Both fixes: claude/hbm-cores-rebal-6-shared-1028 (shared rtl/hdc + tools/die_plan -> ROOT-MERGE).

## driver_rect values (lanes_plain, programme_store) -- plan geometry only, QoR UNCHECKED
driver_rect.py cfg_*2.json -> dr_*.json + dr_*.png (viewed). Plan-fixed SRAM arrays obeying the kit_contract channel
rules (>=10.8 vertical channels incl. core edges, one interior horizontal channel 12.96 per column, 4.32 halo),
island grid ignored; each island overlapping macro+halo gets the nearest 2.16x2.16 driver_rect clear of every
macro+halo. lanes_plain 3x8 (gaps 60.8): max detour 19.1 um, isl0 0; max macro move vs RTLMP 197.7 um.
programme_store 5x9 minus the root slot (gaps 15.4): max detour 87.4 um (isl1-3/13-15 in the edge columns);
max move 118.9 um. Instance order = RTLMP column/row order.
