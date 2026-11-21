# S81-BKSEL-R6 handoff (Claude Opus; successor of S81-BKSEL-R5) -- STOOD DOWN -> S81-BKSEL-R7 (context ~300k, COORD 11-21)

## Done
- Keep edit (dsdv_bk_dsp sd/sl (* keep *), no function change) commit c6c79db984, PUSHED main @4e2b8ec778. Proof+bench rerun oth-ubuntu-1218171 rc 0 (ok SUCCESS, mutw/muts/mutr FAIL, a3p/l4 PASS, l4rrdm FAIL wanted, VMTX vbase+vl4 PASS, BKSEL_L4 PASS). (The handoff hash 9aac5a1e vs my 7a5b7217 is cosmetic: file sha1 3eb4e379 identical in repo, proof_l5, tree_r6, bench_l6.)
- chain_r6 oth-ubuntu-1218164 rc 0: ELAB/BIND 0, LATCHECK PASS 873/873, PRE_PASS, place 0 groups >405, STATION_FAMILIES_OVER 0; R5 left-overs (cp->sd/sl 436, wf->fsp 307) gone; non-reset >300 only u_ids.vr->lo 3 captures 303.4 um (COORD: no row). R2R_MAX 1202.6 = u_rrl_11 -> u_cland_fstart_flt_o0 (boot-only landing writer start, unchanged since R4).
- lef_override (DRT-0073 class) PUSHED main @8d1cff9b1b (commit on branch claude/s81-bksel-r6 in epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r5/repo; log ../push_lefov_r6.log):
  tools/die_plan/lef_overrides/dsdv_bksel_c.lef + dsdv_bksel_q.lef + map.json rows (base_sha256 30d47257... bksel_c_qrx_1117 / 11447d06... bksel_eco3_1117 = the LEFs of the live J6 trees on epyc8/epyc10) + test_lef_override_bksel.py (c PASS, q skip: view not on main).
  Cause: try-3 kit stopped at GRT pin access, DRT-0073 u_sel.u_c/ck[0] (dsdv_bksel_c) + g_q[0].u_q/ck (dsdv_bksel_q; DRT checks unique instances, so g_q[1..3] are the same). The clock pin is the ONLY 0.048-um M5 pin of each signed view (child clock routed wide), at the outline edge under blanket M1-M6 OBS. porous_views.py probe of each view ALONE gives the same 2 DRT-0073 (view-intrinsic). ~240 0.024-um data pins fully under M5 PG straps pass, so it is not parent PG. Fix narrows only that PORT rect to the 0.024-um on-track centre of the same metal; probe 0 DRT-0073 (W/probe_fix_*). Netlist, lib, LEC untouched. Wave bk_sel kits get it automatically (no plan change).
  Evidence: W/pinq1.out (pin neighbourhood: VSS M5 strap x 2097.204-2097.324 over ck[0] column from y 381.98), pinq2.out/pinq.out (per macro edge pins vs M5 PG), probe_dsdv_bksel_{c,q}/probe.log (FAIL), probe_fix_dsdv_bksel_{c,q}/probe.log (PASS).

## J7 rows (state)
- HANDED to S81-J6-ASSEMBLY-R4 (posted; file lanes/handoff/S81-BKSEL-R6-J7-rows.json, committed 021750534d): plan_r6.json 84af570f (epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r5/w) = R3 plan - R3 face/u_stn + rows_face_r5 + rows_stn_ro8 (R4) + rows_l5 + rows_start_r5 (flt_o0 W5) + OT_BKSEL_L4; RTL on main incl keep 4e2b8ec778.
- Bind-measured lane totals (chain_r6 LATCHECK, all delta 0): ca 57, cb 56, xtier_i0 61, idx 111, tp_i0 43, xtier_i1 109, tl_o0 67 (R5 note said 66; ST1 move +1), tp_o0 87, tp_o1 52, xtier_o0 69, xtier_o1 114, flt_o0 17. File w/lane_totals_r6.json.
- Not yet confirmed: J6-R4's ack/merge into J7 (cut 20:00 PST). The lef_override needs no row.

## Running (do not cancel)
- Sign-off kit try 4, unit oth-ubuntu-3077726-1795288283 (epyc7 loved-redfish, 64 GB/16 thr), hub log ~/s81-bksel-r6/sk1.otrun.log.
  Launch: ssh intel2 'export OT_LANE=S81-BKSEL-R6; ot-run --mem 64 --threads 16 --hosts epyc7 --dir /srv/opentallas-scratch2/claude/s81-bksel-r6/w -- bash /srv/opentallas-scratch2/claude/s81-bksel-r6/w/sk1.sh'
  W=/srv/opentallas-scratch2/claude/s81-bksel-r6/w; rt = W/rt_sha12 = 8d1cff9b1bb6 (contains the override); launch tree W/launch_8d1cff9b1bb6 (hardlinks: rt dirs get pruned, 4f62b13 already gone); kit_wave snapshot W/kit_wave_snap.json (fresh at try 4); kit W/kit/bk_sel__t2/gen/bk_sel__t2; route log W/route_s1.log; sign-off kit signoff*/signoff.json.
  sk1.sh = rt_launch_tree.sh tree_r6 + event_gen_spec.py (wave spec_for) + kit-rtl/prepare/gen (src-tree/rtl-root = tree_r6; RGA expanded) + config.mk diff vs wave a14 + run_kit.sh route 48 16.
- My background checks (they die with my session, re-arm in R7):
  * bx5zwc1nd gen check: until grep -q "CONFIG_DIFF_END|exit|DIED" ~/s81-bksel-r6/sk1.otrun.log; then expect "OT_LEF_OVERRIDE ... applied" x2 in W/kit/bk_sel__t2/gen.log, kit lef_override.json, ck[0] RECT 386.400..386.424 and q ck RECT 304.560..304.584 in kit macros/*.lef. Config diff vs a14 should equal try 3's (+A3P/L4 defines, +GLOBAL_ROUTE_ARGS, +LATCH-SWAP TCLs, -OT_GPL_SPARSE_OVERFLOW (leaf-only since FLOW-NOADV-R3)).
  * bw097ynec run waiter: ssh intel2 'export OT_LANE=<lane>; ot-wait oth-ubuntu-3077726-1795288283 --timeout 80000; grep -vE "^ot-(run|heavy)" ~/s81-bksel-r6/sk1.otrun.log | tail -40'
- Earlier tries kept, moved aside: kit_try1_rc11 (src-tree), kit_try2_rc13 ($RG literal), kit_try3_drt0073 (+route_try3.log, LEC exit 0 there).
- Gates: DRC 0, TT setup >= -42, FF hold >= 0, LEC (lec/lec.json), bind+latency (chain_r6 LATCHECK). Post-hook CTS only; visual never blocks.
- Provenance: private kit (tree not src_manifest). If it signs off, report to COORD; the J7 manifest tree carries the rows and the wave re-signs (the override is already on main).
