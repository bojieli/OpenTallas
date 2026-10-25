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

## Update 10:50 PDT (coll A withdrawn; hist_bank contract added)
- slice_station t23 now re-planned here too (coll A withdrawn by COORD: the coll lanes stay). ft_knee_sites gained an
  arclength-target candidate (stations at uniform arclength along the shared Manhattan spine, no forced bank at the
  knee); the allocator keeps the candidate with the fewest banks. t23: ft0..ft3 at their OLD depth (0 added cycles),
  worst paired-bit hop 402.5 um (<=403), every bank a compact row ~110 um x 2.7 um. density taps on banks / face strips.
  test_ft_knee_sites.py: the per-leg axis check became "stations monotone on the spine" (summed Manhattan legs =
  end-to-end Manhattan); PASS3.
- Open plan note (GEOM 10:12): t23 sinks use only x<460 of its 1442x1227 slot; outline right-sizing is a parent-slot
  change, NOT in this delta.
- hist_bank pin contract 359 -> 435 (merged claude/kits-spare2-hb-1025@7d5b9515ca, GEOM-REVIEW-2 PASS): OT_HB_PINCOPY,
  one pin per kept capture flop (clr[16:0], gsel[63:0]), parent hq_parts multicasts; default RTL unchanged; equiv
  17334/17334. dsdv_bksel_q is re-kitted ONLY after hist_bank signs off (needs OT_HB_PINCOPY + the new child view).
- ft_knee_sites now writes regs_um = [in-pin centroid, allocated bank centroids] (was the spine targets, which sit up
  to a half bank-width off the bits when the knee anchor moves to a window edge; G0 measures hops between regs_um and
  flagged 414-442 um on the t23 coll lanes). The candidate reach test also covers the centroid chain. G0 PASS 0E 1265W,
  G0C PASS 0E 1265W on the merged branch (main baseline 0E 1265W). t46 keeps its 660e7287e4 sites (passes either way).

## Combined batch 11:3x PDT (COORD: ONE event)
- Merged main 183f0b03b9 and PATH-S81/COLL claude/path-s81-coll-1025@177137898f (bind.py asbuilt.glue_follows_sinks
  opt-in + 4 lpc C->LP 2-b control lanes, delta_coll_1025.py; bind proof coll_1025_bind_proof.json: strict bind 14,469
  -> 0 unbound). The S81 bind manifest is now in-repo: physical/die_plan/s81/bind/asbuilt_b178_coll.json
  ("glue_follows_sinks": true; = PATH-S81/COLL manifest_coll.json, TOK-DS bind178 base).
- Both delta scripts re-applied on the merged plan: no change (delta_kitsspare2_1025.py made idempotent for core taps).
- G0 PASS 0E 1273W, G0C PASS 0E 1273W (+8 W from the coll lanes); test_ft_knee_sites PASS3; test_bind_glue_follow 4 passed.
