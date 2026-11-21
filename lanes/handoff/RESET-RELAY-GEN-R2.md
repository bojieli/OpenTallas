# RESET-RELAY-GEN-R2 handoff (succeeds RESET-RELAY-GEN-1530; 2026-11-20 PST)

Lane clone: epyc10 /srv/opentallas-scratch2/claude/rrgen-r2/src (worktree on branch rrgen-r2-nested, pushes with ot-push-main). Work dirs:
epyc10 rrgen-1530/r2_t72, r2_t56 (geom.tsv + bound.sv + leg_r2t72/leg_r2t56 outputs), epyc2/epyc9/epyc7 rrgen-r2/gd_<t>/ (geom dumps).

## On main (all pushed, tests green)
- 93b5c48224 form N: hard cores NESTED below a bound instance (any depth) -> plan key reset_pin_relay rows + relay_sites
  (key {inst}.u_rst_pin_relay_{port}.g_r.r[s]); one D per top-level group (cores release together); MR record carries the pin name
  (geom_dump.tcl 5th field, geom_rules macro_rst_pin). bind has no call to stage a nested core, so the RTL consumer
  (OT_BKSEL_L4 RRD in bk_sel) still applies it; kit-rtl / bind ignore the key. NOT yet checked on the bk_sel 7 cores.
- 42eeacf87f reset_tree._free: a site needs a row-high (0.27) and cell-wide (1.08) free run, so the 8.7 um channel u_ha/u_hb
  (cl0cd90c0e rst_rl_137 at 219.58,1092.96: 0.06 um sliver) is no site; push_off picks the nearest legal one. reset_leg_plan
  snaps its stage sites the same way and re-checks hops (report site_snaps / snap_hop_um). Test with the exact case.
- (pending push at time of writing) bank_reset_delta --landing TYPE=landing_placement.tcl: u_bin_<bus> position = centre of its
  landing ring box (u_cland_<bus>), nearest tap, reset.bank_taps, 0 cycles.

## Results
- S81 leaf t72 (epyc2 attempt_17 3_place): legs over 300 um 6 -> 0 (+3 cycles); t56 (attempt_12): 5 -> 0 (+5); t1: dump queued on epyc9
  (epyc9 rrgen-r2/gd_t1.log, ot-run waiting for memory) -> then leg10.sh style run on epyc10 (rrgen-1530/leg10.sh NAME TYPE BOUND GEOM).
- Proofs in flight (unchanged, units in RESET-RELAY-GEN-1530.md): lepe r4, t60 cts, hub_Eo place on epyc10; pv place on epyc7. Not read yet.
- bk_sel geom dump (placed 3_place.odb of fable-fix-s81-bksel-r2/pilot_b1) queued on epyc7: rrgen-r2/gd_bk.log; then run the tool
  with the bk_sel__t2 plan + rtl/s81p_bk_sel__t2_bound.sv and compare with opus-fix-s81-bksel-r4/rows_l4.py (6 flops/core, hop <= 276).

## TODO in COORD order
1 legal-site scan of the current plans (done for the tool; the plan scan is not done); post cl0cd90c0e row to S81-J6-ASSEMBLY
  (re-run reset tree on that bind; rst_rl_137 moves off the channel).
2 u_bin rows for the 14 held KV rows (sys_c a7, hub_Wo a9, 11 pv, hub_Eo): need each kit's bound sv + landing_placement.tcl,
  `python3 -I tools/die_plan/bank_reset_delta.py PLAN RTL_DIR OUT REPORT --types T --landing T=.../landing_placement.tcl`,
  post to KV-PLAN-R2 (D27), cc OPUS-FIX-KV-PV-R3.
3 QC cb rows for the 11 types missing + cbn_q11__cl5cc92dfe 379 um leg (V1 cut 09:30 -> QC-PLAN-R6).
4 bk_sel check, t1 dump. 5 read the four proofs. Post S81-J6-ASSEMBLY (not S81-DIE-R4), QC-PLAN-R6 (not R5), KV-PLAN-R2.
