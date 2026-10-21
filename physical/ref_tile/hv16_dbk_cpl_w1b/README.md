# hv16_dbk_cpl_w1b FALLBACK (SAFE-HBM-DBK 10-21, H.STA.BLK.12) -- WA-LANDED successor of hv16_dbk_cpl_o1
Master `ot_hgi_dma_back_static_vp4_banks_cplw` (rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks_cplw.sv),
FALLBACK of hv16_dbk_cpl_w1: same master, geometry and roots + o1b INVx8 dont_touch drivers on every flop-driven output (OT_OUT_DRV_ABSORB).

Why: daemon routes hv16_dbk_cpl_o1-o1-bc6e7ea9f (MAIN) and hv16_dbk_cpl_o1b-o1b-4929d4bc5 (FB) both FLOORPLAN_MARGIN
bank_distance at 3_3_place_gp: u_dbk.u_control (16 pins) 216.9 um from its pins' centroid. From the route's
fp_margin_lint_dump: the 16 straight nets are wa[11:0] + wb_ready (N face x 426-430) and clk + stk[1:0] (E face);
centroid (436, 513) vs the centre controller (259.2..328.3). Every other port was already landed (l1 in, o1 out).
Options: controller to the N face -- impossible (exact die sub-slot, N row = banks L5-L7); wa pins above the controller --
still 173 um (the controller sits 214 um below the N face). Chosen: wa + wb_ready land in a kept N-face register on
clk_out[3] (the N E-half root that already holds wb_reserve/wb_fill at the wb ports; io_flop_at_pins puts it at the port);
u_control keeps only clk + stk[1:0] straight (3 < bank_min_pins 8) -> bank_distance has no measured macro.
Cycles (die schedule): wa / wb_ready reach the controller +1 edge (ack later is safe; wb_ready is the static first-drain
check, the die holds it one edge earlier). Every other port = _cplo.

Benches (Verilator 5.050, ot-epyc5; logs results/rtl/ref_tile/hv16_dbk_cpl_w1/witness): fold CPL_LAND PASS 7 cmds / 2,769
beats (reference fed the same wa one edge later); banklat BANKLAT_RL PASS die_pre 2 / 2,889 beats; mutants FAIL:
cvraw, wsrelay, fill, nopre, rst, and NEW mut_wa (RL_MUT 4: wa/wb_ready not landed -> CP_FOLD control mismatch).

SAFE-DESIGN checklist: 1 pins FIXED (wa/wb_ready landed at the N face; every other port registered as o1);
2 reach PASS (face reg -> controller pin ~310 um < 405; o1 legs <= ~350 um); 3 fanout PASS (landing regs 1 load each);
4 depth PASS (reg -> wire -> controller pin capture); 5 storage PASS (banks = SRAM children); 6 floorplan: exact slot
606.96 x 542.16 (1.12:1), all children on the 43.2 lattice, util 0.38, channels >= 32 um, no macro at a pin face;
7 clock: regional roots as o1 (clk_out[3] 658 -> 671 sinks, o1 gate spread 36-52 ps), N landing on the existing root;
8 schedule static, +1 edge on wa/wb_ready handed to the die (HBM-DIE15 NOTICE at bind).
