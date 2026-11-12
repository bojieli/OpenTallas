# HBM-GEOM-2 11-12: PHY move+flip, q_mcb_nw re-lay, q_b010 lift (plan deltas, positions/orientation only)

Chain (sha256 first 16 hex):
- base: hbm-cut-1111/compose/t_tapsplit/comb2/die_plan.json `de3584d1e3d89468` (tap-split plan)
- delta_1_phy_flip_mcb_resite.json -> `85bdf1053ce80e66` (phyflip5).
  - u_phy_Q in PHY_NC and PHY_NW moves to [0, 889.92] with orient MX (COORD-approved). PHY_NE is unchanged.
  - The NW W window is clipped to y <= 880, and the shared q_mcb_nw E face is re-laid to match (L21x1, L114wx1, L8x5, L63wx5).
  - q_mcb_nw bit sites are remapped onto the new face order, including the band-entry fan. The q_mcb_nw max hop is now 363 um (it was 446 with the clip only).
- delta_2_qb010_lift.json -> `0a6d5952bee67368` (qb010d).
  - The q_b010 bottom macro group is lifted 17.28 um (S-face pins clear the 10 um halo).
  - 8 stage regs are re-sited to 509.76 so no new hop goes beyond reach.

G0 (check.py --tap-sink-cap error, xtap-sweep tree 7b84010b1c):
- base 569 E / 1864 W. qb010d 571 E / 1864 W.
- The only 2 new ERRORs are face density at the PHY_NW.W / NW_mcb.E window 16859.26: 70 pins in 10 um = 7.0/um against 6/um. This is 5854 pins in 880 um. It needs a per-type face budget, a 3rd pin layer, or an exception.
- WARN 17 new / 17 gone: the same lattice and hop warnings at the new positions.

Strict two-pass bind on qb010d: BIND_OK, 92 partitions / 420 crossings / 0 errors, stale 0, uncovered 0.

pvmw_price.py / pvmw_price_q_sm.json: paper pricing of ot_hbm_sm_pv_merge 233.28 wide in q_sm0..3. It is not a plan of record.
