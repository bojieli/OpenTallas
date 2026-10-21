# hv16_dbk_cpl_o1 (HBM-DBK9 10-21, H.STA.BLK.12) -- OUTPUT-LANDED successor of hv16_dbk_cpl_l1
Master `ot_hgi_dma_back_static_vp4_banks_cplo` (rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks_cplo.sv),
l1 geometry/children/pins + clk_out[3:0]. Fallback in parallel: hv16_dbk_cpl_o1b (same + INVx8 dont_touch pin drivers).

Why: daemon route hv16_dbk_cpl_l1-l1-f5284ed97 EARLY_FAIL_SETUP, post-CTS TT WNS -538.3 / 2,494 endpoints / TNS -689,018
(IO reference). Classified worst paths: ALL child macro -> output port (fanout 1, no logic): u_control -> wb_reserve_base
-538.3 (arc 368.6 + 330 ps unbuffered port wire, slew 1,047), banks -> wd -525..-362 (wire 237-408 ps to S/N faces),
u_cp -> cp_configured -425.8, rq/mv_*/quiet/busy. Inputs +21..+91, macro->macro +106..+211, reset recovery +454: met.
Not fanout, not depth, not clock spread (max root 257 sinks, 36.6 ps): unregistered outputs across 150-500 um.

Structure: every output from a kept face register on a regional root: wd S banks 0,3 / 1,2 -> clk_out[0]/[1], N banks
4,5 / 6,7 -> clk_out[2]/[3]; wb_reserve_* + wb_fill_* (fill keeps its half-way relay) -> clk_out[3]; rq -> clk_land[3]
(adjacent W strip); mv_*/quiet/busy/cp_* -> clk_rst (collar keeps unregistered busy/mv_fault).
Cycles (die schedule): every output +1 edge vs _cpl (wd, wb_fill +2 vs _cp); rr lanes padded to RR_RT-2 = 78 (DIE_PRE 2);
wa returns one edge later (no fault). DIE: hb_dbk_<q> takes 4 more forwarded clock entries clk_out[3:0] (same die clock).

Benches (Verilator 5.050, ot-epyc9; witness/ in results/rtl/ref_tile/hv16_dbk_cpl_o1): fold CPL_LAND PASS 7 cmds / 2,769
beats; banklat BANKLAT_RL PASS die_pre 2 / wd drain+5 / 2,889 beats; mutants FAIL: cvraw, wsrelay, fill, nopre (DIE_PRE 1), rst.

SAFE-DESIGN checklist: 1 pins FIXED (all outputs now registered at the face; inputs landed as l1); 2 reach: face regs at
ports, legs child pin -> face reg <= ~350 um (controller -> N wb), banks -> S/N <= ~250 um; 3 fanout PASS (face regs 1 load);
4 depth PASS (registers + wires); 5 storage PASS; 6 floorplan unchanged l1 (lattice, 1.12:1); 7 clock: 4 new regional
roots (~580-660 sinks each in one face strip), spread checked by the --cts gate; 8 schedule static, cycles above.
