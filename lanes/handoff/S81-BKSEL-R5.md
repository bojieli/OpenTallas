# FLEET-WATCH-R3 handoff (Claude Sonnet; succeeds FLEET-WATCH-2000 and takes FLOW-NOADV-R4's waiter-skip item; 2026-11-21 ~00:00 PST)

## Done
- Push 6 landed (main 304143e8e6): NOPROG/GRT-flat cancel, oom-age victim rule, LAUNCH-SKIP SUPERSEDED (unstarted old-event wave rows).
- FRAC trial ended by COORD ruling: 0 guard kills on all four sampled hosts since 21:59 PST; epyc2+epyc8 reverted to STAGE_PEAK_FRAC=0.5 from bak-fw2000-frac05-1121 (diff = that line only). 0.8 file kept as /etc/ot-heavy.conf.bak-fw3-frac08-1121.
- Pinned-waiter class (COORD high priority): list posted. Cause: kit_wave geom stage = run(roam=False) pinned to the checkpoint host; attempt dir > roam max 3000 MB; kit dirs are host-local disks (/srv/opentallas-scratch2 and -3 are local nvme mounts, NOT shared). Fix REPIN-1121 in tools/autopilot/kit_wave_roam.py run_watch + kit_wave.py run(): geom not admitted in 30 min -> copy attempt dir to a host that admits it now, run there, copy back. Tests test_kit_wave_repin.py. Clone epyc7 /srv/opentallas-scratch2/claude/fleet-watch-r3, commit fc5be0243b, push log ../fleet-watch-r3.push1.log (ot-push-main --test-timeout 3000 running).

## Open
1. Push fc5be0243b: if rejected, fetch, rebase, rerun with --test-timeout 3000.
2. Re-queue the stuck geom waiters (epyc2 12, epyc10 5, intel1 2 pinned; all admit 0 GB): after the push is in rt/current, stop each exact wave unit with ot-run --cancel <kw-... unit> (the unit that parents the waiting ot-run client) so the wave relaunches with REPIN; do not touch admitted jobs. Client pid -> unit via tag otrun-<host>-<pid> in the waiter cmdline.
3. Waiter skip for unadmitted old-plan waiters (s81 dsdv_slice_c1x_C__t6 / t8 old event 465cb9fe2d3, 48 GB on epyc2): their wave rows are RUNNING (wave unit alive, ot-run client waiting), so superseded_unstarted does not see them. Needs: waiter -> wave row match (client pid tag -> wave unit), and a stop of the unadmitted client only. NOT built yet.
4. epyc2 root 89%: kw43-wave-1109n (1.27 TB) is PROTECTED and referenced by live sealed jobs, static since 11-09; kw45 555 GB (live_qwen_compute 61 GB..., per-entry du /tmp/fw3_kw45du.txt on epyc2); no growth found, nothing deleted.
5. Rule slip: I ran rm -rf on my own pytest basetemp (.pt in the r3 clone); use ot-delete in future.

## 11-21 BIND RESULT (chain_r4c, measured from the bind, LATCHECK PASS 873/873, PRE_PASS, bind + GEN OK incl. landing_writer_start flt_o0 W5; G0 skipped)
Lane total cycles (latcheck table = bind_plan_cycles), R3 -> R5: ca__s_0N_LP__bk_sel 55->57; cb__s_0N_LP__bk_sel 54->56; xtier__s_4S_C__bk_sel 59->61;
idx__svc_14__bk_sel 107->111; tp__s_7N_LP__bk_sel 39->43; xtier__seqhost__bk_sel 104->109; tl__bk_sel__s_0N_LP 63->66; tp__bk_sel__s_7S_LP 82->87;
tp__bk_sel__s_7N_LP 47->52; xtier__bk_sel__s_4S_C 67->69; xtier__bk_sel__seqhost 111->114; flt__bk_sel__gunit 12->17 (incl. the boot-only writer start W5? no: data +5 from the 13-station chain).
(Plan fixed_cycles: cb/ca/xtier_i0 3, idx_i0 12, tp_i0 11, xtier_i1 11, tl_o0 10, tp_o0/o1 16, xtier_o0 5, xtier_o1 10, flt_o0 13; files w/lane_deltas_r5.json.)
Plus L4 (RTL on main): loop lane +4, t_o +1 (RO 8), fault +3, dst/lpe +3, core reset release +6. J6: vmux recompile from these LAT_*, then token sim.
Placement + hop scan: place_r4c running.

## PLACED RESULT chain_r4c (place_r4c rc 0, geom_r4c, hop300_r4c.json in /srv/opentallas-scratch2/claude/s81-bksel-r5/w)
r2r max 1,202.6 um (R3 1,318), 2 captures > 405, 304 > 300; STATION_FAMILIES_OVER 0 (no bus / station / face / landing-start / hub family over 300 any more; R3 had 2,714 > 300).
Of the 304: ~297 = die reset tree u_rrl_* at the bound 380-um pitch (J3 bind, not this type's rows). Remaining non-reset families (7 captures):
- u_rs.rq -> u_core.rs1 705 um (1): rs1 (dsdv_idx_l20s.sv:1197, resets dst/lpe/lp_q) sits at (2161,1086) by the u_tx N edge, its reset rq at (2170,389). Needs RTL: a reset relay stage between rq and rs0/rs1 (dsdv_bk_rrd form, ~3 stages), not a row.
- u_dsp.g_r sd -> cd 372, u_dsp.dst -> u_ist_{tl,tp}_o*_0 363-368, u_ids.cp -> u_dsp.sd 337-340: dst/lpe/wf unsited at (2298,1086) vs ist_0 at x 1926-2121: relay_sites for u_core.u_dsp.dst/lpe/wf at ~(2060,1085) and the g_r chain on the ids.cp -> dst path (next iteration, rows only).
Plan for J6 = plan_r4c.json parts: rows_face_r5.json (3,671 relay_sites + 12 internal_stations + lane fixed_cycles), rows_stn_ro8.json (R4 dir), rows_l4.json (R4 dir), rows_start_r5.json (clock.landing_writer_start), lane_deltas_r5.json.
