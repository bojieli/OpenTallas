# FABLE-FIX-HEAD-LEP0N-R6 (Fable, 11-21 19:35-20:4x PST): hd_lep0N type split, tool keys landed, floorplan blocker (successor of R5)

Predecessors: lanes/handoff/FABLE-FIX-HEAD-LEP0N-R5.md (cut census, tools), -R4.md (RTL facts, rename map), lanes/FABLE-PD-HEAD-2000.md.
Lane dir intel2 L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-r6 (clone = lane clone of main, plan/, tmp/).
Stood down on context. NO kit launched, no split run, no plan event, no live tree written, nothing resealed.

## In flight (1 unit, adopt it)
- oth-ubuntu-1136304-1795317736 (epyc9, six-content 0-cycle equivalence, R4's). Still in "6. EQUIV_INDUCT" at 20:3x PST
  (349,132 of 351,685 proved by equiv_simple; proof log last written 19:29). NOT proven. Pass = PARTS_EQUIV_PASS.
  Hub log intel2 ~/fable-fix-head-lep0n-r4/parts_equiv_e9.otrun.log. Re-arm: ot-wait oth-ubuntu-1136304-1795317736.

## Landed on main
- 6dbb162ffe8 type_split.py (ot-push-main, full test file run): the 3 type keys and 14 clock keys of HEAD.
  - id_straps: every piece keeps the row; a site outside the piece is re-seated at the same distance from the nearer
    type edge (report id_strap_sites_reseated). Assumes each piece partition reads strap_rst_ph at its own reset entry.
  - private_reset_start_exports copied; reset_start_raw_exports only via spec drop_type_keys (new key), fail closed.
  - clock scalars + tap_group copied (CLOCK_COPY_KEYS); start_capture_um = piece tap + base offset; reserved_sites_um
    rows follow their rect (a rect across the cut fails closed).
  - landing_reader_start, landing_writer_start, landing_status_anchors, landing_status_input_stages, reset_tree_anchor
    stay spec drop_clock_keys. THE RE-DERIVATION TOOL FOR hd_lep0N IS NOT IDENTIFIED: head_cland_stage_delta.py TYPES
    does not list hd_lep0N; head_reset_exports.py fix re-derives reset_start_raw_exports. Find which NF15f prep step wrote
    the lep0N START / status keys (prep dir nf14_report.json, republish_hd_lep0N.log) before the first split run.
  - 4 new tests (test_type_split.py, "_head_keys_split"). Unit level; no HEAD type has run through Event.run() yet.

## BLOCKER for COORD: the 907.2 cut has no E sites for the 5 u_land SRAMs
Measured on plan_parts.json with L/tmp/occ.py (every hard core, stage row, relay / tap / strap / START / reserved point):
1. u_land SRAMs are 91.8 x 39.43. The E half of the N-S street is 60.48 wide (907.2-967.68), so g_t[2..4]
   (x 861.0-952.8, y 350-475.8, between pairs 2 and 3) cannot stay in the street. Free 91.8 x 39.43 sites in the whole
   E piece: (1310.28, 799.28), (1552.2, 799.28), x 1673-1750 y 704-800, the E strip, the N strip x 939-1051 y 1344.
   None is within 400 um of the u_land rows (wdq / mrd / mlwd / rid at x 916-1265, y 485-675).
2. The band strip y 604.8-659 (x 969-1500) fits u_land only if the RX row y 638.28 is evicted and relays are nudged, and
   then holds 3 (x 1010.99, 1157.87, 1344.84); it is cut up by mlwd_h2 / mlwd_h3 / rid_low, the clock tap (1131.84,
   596.16), the count straps and the START stages.
3. L/tmp/moves.py does all moves by rule (u_land at fixed sites, RX by nearest free site with the PD row rule, rows
   after their macro, TXI / KRX row renames). Its output L/plan/plan_parts_moved.json is PROVISIONAL AND BAD, do not
   build it: 23 macros move, lane 2 RX banks land 500 um from their rows (x 1400-1570), g_rx[0] / g_rx[3] are scattered,
   wdq_bank2/3/4 and mrd rows are left behind. L/plan/moves_report.json has every row.
Options:
- (A, my recommendation) cut at x 846.72 (98 x 8.64, the E edge of pairs 1 / 2; any lattice x in 846.72-967.68 is in
  the street, R5's "907.2 only" was too narrow). g_t[2..4], 4 of the 8 RX banks, rxbank_l2b*, krx2_r4, txi*_s0, c0i_s0
  then lie in E untouched. Moves left: g_t[0], g_t[1] (free after evicting 2 RX banks: (1010.99, 604.81), (1157.87,
  604.81)), 4 RX banks (x 794.99; column x 913.07 has a free slot at y 583.21, strip y 604.81 has more), wdq_bank0/1,
  krx1_r4, krx1_s1, krx2_s1. Price: the W piece's cut face is free only in the band y 509.76-846.72 (337 um; pairs abut
  the cut): h2r + r2h of lanes 1, 2 = 2,264 bits = 6.7 / um, and coll_i0 (514, N window in W) crosses in the N strip
  (69 um, 7.4 / um). Both are over the plan budget 6 / um and under clip_max_pins_per_um 8. rs1 / rs2 must then be a W
  local reset fan (no cut bits). Check that a pair flush on the piece edge is legal (halo, PG) or use 855.36 (then all
  8 RX banks and rxbank_l2b4 move, g_t[2..4] still stay).
- (B) keep 907.2 and hand-draw the E band: evict the RX row, u_land in the strip + 2 at y 799.28 with their wdq / mrd
  rows, i.e. a re-floorplan of 25 macros and about 40 rows with a visual review. Needs the u_land data flow first
  (PLW stages come from the E strip: plw_s2 (1845, 828) -> s1 (1736, 598) -> s0 (1426, 598) -> mlwd -> wdq -> SRAM -> mrd).

## Other facts found
- Hub rows txread_l{0..3}b* with prefix u_core.u.u_lep.u.lo<i>_d are probably dead after the TX extraction (the hub
  instance leaves lo<i>_d unconnected, base/split_tx_io_stages.sv 1568-1571). Verify in parts.il, then native_stage_drop.
- RX banks W of 907.2 are 8 (g_rx[1], g_rx[2] banks 0, 1, 3, 4); bank 2 of both is already E (x 913.07).
- TX SRAMs of lanes 1, 2 are already W (x 69-670); they free no E site (R5's note was wrong).
- TXI 4 -> 2: surviving g_s[0], g_s[1] of lanes 1, 2 take the sites of old g_s[2], g_s[3] (W); KRX 6 -> 4, RA 3 -> 2:
  region g_rxf.g_s[0,1] / g_rxr.g_s[2,3] on old sites r2 and s1, hub g_rxf.g_s[2,3] / g_rxr.g_s[0,1] on s2 plus ONE new
  E row per lane (moves.py "krx<L>_s3"). Names change, so the cut form needs its own equivalence run.
- Draft spec L/plan/split_spec_1cut.json (one cut, drop keys, net_drivers of the 6 crossing nets). clip_windows form
  (bool or list) not checked against Event._clip_windows.

## Work order left
1. COORD picks (A) or (B). 2. Site moves (edit LAND / rules in moves.py, or spec core_moves, which validates tracks).
3. PARTS_EQUIV_PASS, then cut-form RTL (RXA 16'h0220, TXI 16'h2222, W local reset fan) + cut-form equivalence.
4. Private tree (real copies, nlink 1): gen.py rtl of the six-content plan, cohort, strict bind 26/26, LATCHECK 329/329.
5. Split, re-derive START / status / reset-tree keys per piece, strict bind + LATCHECK + G0.
6. kit_wave.py private-spec W and E (intel2 gen; build host per current disk state), --ab OT_PREGRT_HOLD_R2R_MARGIN=<measured>.
7. Routed LEC, sign-off, reseal r17a.
