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
