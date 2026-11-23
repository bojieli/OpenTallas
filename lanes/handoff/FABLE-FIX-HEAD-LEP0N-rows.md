# FABLE-FIX-HEAD-LEP0N plan rows for hd_lep0N split (r18f = r18e + 2 fixes), 11-22 03:5x PST

Tree (epyc9, ot-tree-fork of Codex r18e b4f489665c04, private, sealed at kit gen):
/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122/trees/s81_head_r18f_ringff
Plan sha256 f23abfbd22780d25 (r18e e84371ca5dcf). Gates on r18f (unit oth-ubuntu-2529493-1795347713, log intel2
~/fable-fix-head-lep0n-1122/chain_r18f.otrun.log): plan_gate_pre PASS findings 0 (ref tools rt 6d2e187f0d65), strict bind PASS,
cohort 27/27, LATCHECK 334/334, hd_lep0N_w wrapper byte-identical (138a7ee6c0f6), hd_lep0N wrapper 54dde234 -> 94a6b116.
Scripts: epyc9 .../fable-fix-head-lep0n-1122/tmp/{ringff_fix.py,face_rows.py,patch_cl.py,chain_r18f.sh}; reports in the tree prep dir
lep_ringff_1_report.json, lep_facestat_1_report.json.

## 1. LEP-RINGFF-1 (hd_lep0N_w, plan only) partition_types.hd_lep0N_w.clock.landing_contract.bands (+ collector_local_sources[].band)
- coll_i1: rect_um [17.28,634.24,58.32,840.24] (unchanged), ring_place "ff", spread 1.8697, band_spread_target 2.0, area_reserve_um2 4521.621;
  drop ca_reserve40_um2 / band_use_target / band_use.
- coll_i2: rect_um [17.28,110.16,30.24,336.96] (was [17.28,17.28,30.24,548.64]), ring_place "ff", no spread, area_reserve_um2 2134.84
  (flops-only reserve x 1.05), max_pin_to_band_hop_um 144.2 (was 355.88); drop the same three keys.
Cause: fable-fix-head-lep0n-r7/tmp/recompose_merge.py compose(band_reserve='padded', band_ring='all', ring_ff_min_bits=0).
Measure: r18e W placed TT -495.73 / -204.08 / -135.10 (u_cland_coll_i2), tns -62198; tag ring:coll_i2 (r16: ring:coll_i2@2.0666+ff).

## 2. LEP-FACESTAT-1 (hd_lep0N E piece, plan + generator)
- partition_types.hd_lep0N.clock.landing_status_input_stages.agg.i_coll_i0_p =
  [{xy_um [10.0,1069.52]}, {xy_um [69.08,810.0]}, {xy_um [387.68,810.0]}, {xy_um [706.27,810.0]}]  (street path, hop 318.6 um)
- partition_types.hd_lep0N.clock.landing_local_resets += f0 rst_rl_602 @ [10.0,1069.52], f1 rst_rl_384 @ [69.08,810.0],
  f2 rst_rl_355 @ [387.68,810.0], f3 rst_rl_193 @ [706.27,810.0] (consumers u_cland_sin_agg_i_coll_i0_p_0..3, depth 7)
- tools/die_plan/clock_landings.py: target "agg" of landing_status_input_stages accepts a same-region (mask.intra_inputs) status
  input; relays sit between its face flop Q and agg_1. +4 status cycles on that input only, 0 data cycles. Patch in the tree; to main next.
- published/ot_s81hd_lep0N.sv republished (4 x ot_dp_landing_collect N=1 + 4 x u_cland_lrst_f*), wave_prepare digests refreshed.
Cause: head_sideband_street_rows.py routes only mask.inputs (landed rings); the cut-leg child i_coll_i0_p is mask.intra_inputs.
Measure: r18e E placed (3_detailed_place.rpt 11:37 UTC): u_cland_face_fault_i_coll_i0_p -> u_cland_agg_1 TT -800.56 (1.6 mm, one hop),
tns -49481. Other E groups at place: coll_i3 lap_ok -191.73 (max_delay 416.5, pre-repair), all else met.

## 3. Settings (done): kit_wave.json dies.s81_head.item_env.hd_lep0N_w = the hd_lep0N row (coord 424a945b2b91).

## Builds
- MINE (one): hd_lep0N_w from r18f, spec ~/coord/autopilot/private_specs/FABLE-FIX-HEAD-LEP0N/s81_head_hd_lep0N_w_1122035312/spec.json,
  goal finish, sealed, run-item = systemd --user unit fable-lep0n-w1 on intel2 (pid 339647), log ~/fable-fix-head-lep0n-1122/runitem_w1.log.
- R8: build hd_lep0N (E) from r18f, NOT from r18e (r18e E fails the status path by -800). The E kit gen needs the patched
  clock_landings.py: it is in the r18f tree tools; an rt with it follows after ot-push-main (posted when landed).

## 4. LEP-RINGFF-2 (hd_lep0N_w, plan only; added 05:0x after the r18f W placed DB) tree r18g
- coll_i1: rect_um [17.28,629.64,30.24,864.0] (was [17.28,634.24,58.32,840.24]), ring_place ff, no spread, area_reserve_um2 2134.84.
Cause (measured, r18f W 3_place.odb, epyc9 L/sta_w/w_xy2.txt): the pin column of coll_i1 is y 640.39..845.59 but the band ended at 840.24
(pair 1 halo), and its START pin (y 932.9) is nearest the LAST bit 513. landing_placement.tcl cland_place_pinslot puts each flop in
[target row .. band top]; for the top 5 um of bits and the 102 control registers keyed at bit 513 that window is empty, so they fall
back to first fit at the band BOTTOM: ctl_w / ctl_lap / g_oh / ghi / glo FIRM at y 634.5-635.6, rv / lap_ok FIRM at y 839.5.
Placed TT: ctl_w[1] -> rv -708.55, ctl_w[2] -> lap_ok -548.8 (max_delay 416.5 across 205 um). coll_i2 (band covers its pins, START pin mid
window): rv -19.5, all groups met. New band = the 12.96-um W channel over the whole pin column + 18 um above it (beside pair 1).
Tree epyc9 .../fable-fix-head-lep0n-1122/trees/s81_head_r18g_ringff2, plan sha256 0c7056cd38b8b1f6; landing_band_core PASS 0 new;
plan_gate_pre: only TOOLSTALE vs rt c9b8d5f226ca (tree tools are 6d2e + overlay; kits take the rt tools).

## 5. Same class on the E piece (for R8, read from the r18e E place log + STA; not built by me)
- lepk_i0: band y 265.59..501.13, pin column y 265.80..510.98: the top 9.85 um (about 44 bits, 260 flops) fall back to first fit at
  the band bottom, 245 um from their pins. Matches the 51 violating u_cland_lepk_i0 .. u_dsel/y path-delay ends (-48.9) and
  reader_start_lepk_i0_2 -> dsel -191.4. Row: band top >= 512.5 (or rects_um).
- coll_i3: band y 854.29..941.08 but pin column y 645.43..759.43 (sidecar has the band on the pins [980.64,645.19,1054.08,759.64]);
  every ring flop is 95-296 um from its pin and the 84 control registers are keyed at bit 1, 135 um from START. E7 CTS fs_q -> wen -216,
  r18e place lap_ok -191.7. Row: band on the pin window if the io stage rows (pin_s0u, pout_s7c at y 686-704) can yield, else ff_rect_um.
- Guard to add (tool): fail closed when a +ff y-column band does not cover its pin column / the ctlkey bit has no rows above it.

## 6. LEP-RSTART-1 + LEP-RSTART-2 (hd_lep0N_w START relay of the relay piece; plan + republished W wrapper) tree r18h
Measured on build A (r18g W), CTS post-hook: every ring group met (path delay worst -1.28); setup_ws -347.30, tns -16,424.8 is one
cluster, the START fan of the relay piece: u_cland_rstart_rx sits FIRM at the fstart_out pins of the W face (y 1154.5, copy y 453.6).
- RSTART-1: clock.landing_local_resets k3 (raw rst_rl_287 @ [10.0,792.88]) consumers += u_cland_rstart_rx. Was reset by
  cland_reset_coll_i0 from (814,1085): 810-1440 um, -347.30 / -322.57.
- RSTART-2: clock.landing_reader_start = {depth 2, origin_rect_um [2.14,1145.89,19.42,1163.17], branches
  coll_i0 [[131.61,1370.0] rst_rl_258, [485.61,1370.0] rst_rl_256], coll_i1 [[10.0,589.36] rst_rl_157, [10.0,739.98] rst_rl_287],
  coll_i2 [[10.0,335.11] rst_rl_169, [20.54,220.51] rst_rl_167]} (street path, hops 354 / 151 / 126 um). Was the default reach form
  (one stage at the ring): rx -> u_cland_reader_start_coll_i0_0 970 um, -183.4 x 33 ends. Boot +1 cycle on the W rings, 0 data cycles.
  landing_writer_start is refused on a relay piece (no FSTART face flop), so the rx flop stays at the fstart_out pins.
Tree epyc9 .../fable-fix-head-lep0n-1122/trees/s81_head_r18h_rstart, plan sha256 301a0f1635d65898: plan_gate_pre PASS (TOOLSTALE skipped,
tree tools 6d2e), bind PASS, cohort 27/27, LATCHECK 334/334 (epyc9 L/bind_r18h2).
Die-level note (not a type gate): cland_rstart_in enters W at the cut face (818,747) and its rx flop is 1.2 mm away at the W-face pins.

## 7. LEP-PAIR-RSTPIN-1 (COORD ruling option b; ot_s81hd_lep_pair, all 4 instances: rg0/rg3 in hd_lep0N, rg1/rg2 in hd_lep0N_w) tree r18k
- New SIGNED pair view results/head_lep_pair_views_vE28s_1122 (in tree r18k): rst_n BPin M5 on the S face (399.372,0)-(399.396,0.192);
  pin-move ECO on the signed vE28 DB, only net rst_n re-routed (257 um), DRC 0, 1,101,619 insts; sign-off SIGNED (minimal profile) TT setup
  +13.98, FF hold -182.94 boundary, pair skew 77.0/64.2. sha256: lef a18a0f164d454448, tt.lib b06737eb11e43fc3, ff.lib acca9f17f1cdd633,
  clock_contract d41f12d068b9b3d4 (clk pin-register mean TT 558.17, was 553.42). Work dir epyc9 fable-fix-head-lep0n-1122/pair.
- core_pins/lep_pair_pins_777s.json = 777 with rst_n {M5, 399.384, 0.042} (777r's x 397.464 is the signed clk entry: not usable).
- hard_cores rows (4): pins_file core_pins/lep_pair_pins_777s.json, lef/lib -> the vE28s dir.
- Consequence handled in the same tree: the pair reset gate taps follow the pin (E: tap 204 (535.7,1343.5) -> (546.3,842.4), tap 205
  (535.7,13.0) -> (525.1,514.1)), the reset trees are re-solved and renumbered, so head_reset_exports.py fix + L/tmp/rekey_resets.py
  (sites kept, raw relay names re-picked: 13 rows on hd_lep0N, 4 on hd_lep0N_w) + both wrappers republished.
Tree epyc9 .../fable-fix-head-lep0n-1122/trees/s81_head_r18j_pairs (= r18h + this), plan sha256 762441fd7f142bf6: plan_gate_pre PASS
(TOOLSTALE skipped), reset exports check PASS, bind PASS, cohort 27/27, LATCHECK 334/334 (L/bind_r18j2).
Kits from r18k, goal route, sealed, rt c9b8d5f226ca: E spec s81_head_hd_lep0N_1122094359 (unit fable-lep0n-e1), W spec
s81_head_hd_lep0N_w_1122094408 (unit fable-lep0n-w9).
Open on W (build A probe, GRT 8 iterations): vertical congestion in the W channel at the top of the two ring bands (x 0-60, y 300-350: 1,073;
y 850-900: 478) and in the TX SRAM mid band (x 210-660, y 600-700: about 3,900); the two pair-centre rst_n nets (capacity 0) are removed by
this view. 30-iteration probe running (intel2 L/grt_probe30).

## 8. VOID (retracted 19:1x: generates no register; do not apply the station / lane rows; hd_host_n row is valid) LEP-H2R-STN-1 (hd_lep0N E piece, plan only) + merge row -> tree r18m = MERGED PLAN CANDIDATE
- partition_types.hd_lep0N.internal_stations += {conn bus:o_h2r1_p, launch u_core.h2r1, from_um [344,605], to_um [0,795.312], regs_um [[200,720]],
  bits 574} and {conn bus:o_h2r2_p, launch u_core.h2r2, from_um [344,605], to_um [0,625.536], regs_um [[215,612]], bits 574};
  lanes L2 / L4 fixed_cycles 1; latency.lanes L2 / L4 {cycles 3, fixed 1, natural 3}. +1 cycle on the two hub -> W-piece cut lanes.
  Measure: r18e E placed u_bout_o_h2r1_p/q 186 ends worst -229.6; geometry g_mtx (399-414,575-578), stamp logic mean (344,605), face register
  (4-10,758-832): 560-650 um after 440 ps of logic. Hops with the station 259 / 301 um (h2r2 136 / 229, kept equal to lane 1).
- partition_types.hd_host_n = R8 r18j row (pg_pin_rule true).
Tree epyc9 .../fable-fix-head-lep0n-1122/trees/s81_head_r18m_e2, plan sha256 3dd49f406010fc3a = r18k + section 8: plan_gate_pre PASS, reset
exports check PASS, bind PASS, cohort 27/27, LATCHECK 334/334 (L/bind_r18m). E kit e2: spec s81_head_hd_lep0N_1122104411 (unit fable-lep0n-e2,
rt a4c5d882015d). Still unaddressed E placed-scan groups (R8 kit geom/placed_scan.tsv, 22 NEED-STATION): u_land.rd -> g_rxm dm 657 um,
g_rx.wp -> qwa 615, u_rg3 g_txr -> credit_pin_r 986 (9 bits), u_land SRAM -> rd 625; internal reg-to-reg, need RTL stages, not plan rows.

## 9. LEP-RSTART-2c (hd_lep0N_w, site rows; fixes my section 6 sites) tree r18n, plan 341dbb140f8fb054
clock.landing_reader_start.branches: coll_i0 stages xy [131.61,1380.0], [485.61,1380.0] (were y 1370.0, on the status relays / lrst k12:
w10 place died "OT_CLAND no legal site u_cland_sin_coll_o1_coll_i0_0"); coll_i2 stage 1 xy [10.0,222.0] (was [20.54,220.51], inside the
coll_i2 band). No origin_rect_um on the relay piece. Raw relay names re-keyed (L/tmp/rekey_resets.py). Check tool: L/tmp/sites.py PLAN TYPE.

## 10. LEP-TXI-SITE-1 (hd_lep0N_w, site rows, 0 cycles) clock.landing_contract.native_stage_groups rect_um by tag
stage:txi2_r0 [497.88,568.62,508.68,711.06] (was [732.24,599.4,743.04,741.84]); stage:txi2_s0 [230.04,562.14,294.04,574.14] (was
[560.24,673.04,624.24,685.04]); stage:txi1_r0 [532.44,639.36,543.24,760.58] (was [710.64,610.74,721.44,731.96]); stage:txi1_s0
[176.58,752.22,240.58,764.22] (was [580.24,660.62,644.24,672.62]). Measure (w11 placed): stage 1 x 560-643 -> g_safe_write wp_r x 23-544,
up to 690 um, CTS post-hook -136. Three hops of about 300 um now (cut face -> stage 0 -> stage 1 -> write pointers).
## 11. LEP-RINGCTL-1 (hd_lep0N_w) partition_types.hd_lep0N_w.place_regions += 3 x {name ringctl_<bus>, kind soft, cone between, radius_um 24,
centre_um coll_i0 [740,1376] / coll_i1 [21,843] / coll_i2 [21,232], inst_re u_cland_<bus>/(u_ring\.(ctl_w|ctl_lap|g_oh|glo\d|ghi\d|tc)\b.*|lap_ok.*|rv\$.*)}
Measure (w11): control regs within 10 um of rv / lap_ok on all rings; CTS -272 (coll_i1) / -185 (coll_i0) from the logic cone. Needs rt >= 2a24a958d719.
## 12. LEP-RSTART-RX-1 (hd_lep0N_w; tool main 345ac19b04b3) landing_relay_rx_stages 3; relay_sites u_cland_rstart_rx_p0/q [552,754],
_p1/q [300,754], _p2/q [10,812]; sidecar re-bind (count_aligned parts.lep0N_w stages 2 -> 5, K +3) by R8. NOT in r18p (needs the sidecar).
Sections 10 + 11 + strip of the void section-8 rows = tree r18p (epyc9 .../trees/s81_head_r18p_w12), plan 0fc19ee36f705903: gated with rt
2a24a958d719 via composed launch tree (no tool copy): plan_gate_pre vs base 5e1f38e1530b PASS 0 findings, bind PASS, cohort 27/27, LATCHECK
334/334 (L/bind_r18p). Probe kit w12: spec s81_head_hd_lep0N_w_1122204549, OT_PROBE_THROUGH=1.
