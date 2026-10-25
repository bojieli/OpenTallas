# KITS-SPARE-2 batched S81 plan delta part (COORD rulings 2026-10-25 10:23 items 2, 4, 5)
Script: physical/die_plan/s81/delta_kitsspare2_1025.py (idempotent; base main 55b7f92771).
- (2) early core taps (clock.core_taps early; BUDGET until the core SIGNED TT pin-reg mean replaces it):
  bk_sel__t2 u_bk_sel.u_sel.u_c dsdv_bksel_c 430 ps TT (early 180) at its E-face ck[0] channel (3736.9,167.1);
  gunit__t1 u_gunit.u_l5 dsdv_gunit_l5 520 ps TT (early 270) at its W-face clk channel (1531.6,135.9).
- (4) ot_s81sl_xrt3 570.24x395.28 (5.8% fill) -> 207.36x164.16 (38% of 13,083 um2 placed cells). Pin-limited (9122 pins):
  faces keep their pins and group order, re-spread uniformly; N/S M3+M5 (S 8.3/um/layer), E/W M4+M6 (<=7.1/um/layer)
  = M6 pin grant, obs_max M5 -> M6. Placed centred in the old slot x, top edge on the cap/xfin top line (MX parent).
  All pins on the parent-type plan tracks (core-frame offsets from origin + track_offset, MX). pinhash recomputed.
- (5) slice_station__t46: Manhattan knee bit sites (tools/die_plan/ft_knee_sites.py), 0 added cycles (stations 4/4/4/4,
  max paired-bit hop 362 um) + clock.tap_mode density (target 600 / max 1500 / radius 150): 12 taps, each on a
  station bank or face pin-reg strip, 0 empty, max sink distance 64 um (was a 16-tap 400-um grid, 7 empty).
  slice_station__t23 NOT here: it carries only coll__lk_ES0/ES1 <-> s_7S_LP, which the coll decision A removes
  (PATH-S81 part). Knee sites there would have cost +1 cycle on 3 slots.
Gates (epyc1, this tree): G0 PASS 0E 1265W (main 0E 1265W); G0C PASS 0E 1265W; latency table unchanged.
Renders BEFORE|AFTER in img/ (viewed). Note: the BEFORE xrt3 pins in the c3x panel are drawn from the new table (render artefact).
