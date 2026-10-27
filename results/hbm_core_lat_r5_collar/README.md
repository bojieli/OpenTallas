# HBM-CORE-LAT-R5 collar_idx256r (ot_hbm_static_cfg_collar_idx256r) - right-sized outline + rebalanced pins (2026-10-27)

Why (COORD 02:20 spot-check + R4 02:21 collect): R4 on the B2o 108^2 outline measured post-CTS pin-register insertion
TT 282.9 / FF 220.2 at GRT RC (postcts_gate, CHECKED from the R4 kit log; 273 at placement RC), FAIL_POSTCTS on TT.
Root cause: outline ~35% empty (34% util), 1244 of 1560 pins on the N+E faces (N 622, E 622, S 304, W 12) -> logic
pulled to the pin faces, long local clock tree. COORD: no more trunk; shrink the outline, rebalance pins.

## Trial outline (gen_r5_collar.py, from the R4 kit; no RTL / netlist change)
- 86.4 x 86.4 um (20 x 4.32 lattice; was 108 x 108, -36% area). Core 4.32..82.08. Placed util 55% (3302 um2, run_place.log, CHECKED).
- Centre clock-entry island 38.88..47.52 (8.64^2, on the lattice), clk pin M5 at (43.2, 43.2).
- Pins 1560 -> N 389 / E 389 / S 392 / W 389, 0.192-0.24 um spacing on the 0.048 track grid, span 2.184..84.216 (CHECKED from pins_r5.json).
  Face choice follows the planU2/planS2 station geometry (root internal_stations, CHECKED there):
  - W: rec[0..220] + c_busy/c_fault/go (all go to u_hb_argmax, which sits W of the collar; R4 had rec on N), tgt, clk_in, rst_n, c_done__W, pw_data[0..147]
  - E: prm[0..388] (root face buses L124/L64/L80 land on the E side)
  - S: prm[389..672], pw_data[148..255] (pw_data's first station is S of the core)
  - N: cfg_v/desc_v/launch_v/cfg_target/cfg_addr/cfg_data (L74m_i lands N), active/fault/ready/c_done/pw_we/start_v/pw_addr, prm[673..768]
  pw_data goes to both root faces (x 0 and x 1684.8), so its W/S split costs no extra length. Proposal to HBM-MU-QUAD-3 (planU2 delta):
  the slot and the station re-siting are theirs.
- Trunk: unchanged 12.8c chain 7 x BUFx10 FIRM in the entry island (no added trunk). Plan recheck: R3 tree model 94.9/75.9 scaled by
  the outline (x0.8) plus the R4 measured calibration (+30.2 TT / +30.9 FF, tree = measured - trunk plan 157.8/113.4) gives
  need 144 TT / 111 FF; trunk_chain.py's own pick metric still picks BUFx10 x7 -> same trunk.
  PREDICTED pin-register insertion TT ~264 / FF ~205 (PLAN MODEL, UNCHECKED; band 250+-20 / 202.5+-20).

## LEC
- in-kit synth LEC (no opt-in): UNPROVEN 9367/9380, the 13 dead rec bits (u_bout_rec.q[0..2] class) as in R4 (lec_synth_r5.json, CHECKED).
- R4 synth LEC with OT_LEC_SUPERSET_VEC=1: EQUIVALENT 9393/9393 (R4, CHECKED there).
- tools/die_plan/lec.py: with OT_LEC_SUPERSET_VEC=1 lec.json now records superset_vec = {n_extra, extra_bits, unobservable PROVED|NOT SHOWN}
  (COORD RULING HBM-CORE-LAT-R4 (3)). The routed LEC in chain_r5.sh passes the flag explicitly.

## Runs (intel2)
- placement: unit oth-ubuntu-602157-1793093581 exit 0; render collar_r5_placed.png (viewed: logic evenly spread, small voids NE/E, island centred).
- chain_r5.sh (finish -> signoff tt,ff -> routed LEC with the flag): unit oth-ubuntu-763084-1793094169, started 02:42:50 PDT.
  Collect: /srv/opentallas-scratch2/claude/hbm-core-lat-r5-collar/kit/{chain_r5.status, postcts_gate_TT.log, postcts_gate_FF.log,
  signoff/signoff.json, lec_routed/lec.json, FAIL_POSTCTS|FAIL_PREFLOOR}.
