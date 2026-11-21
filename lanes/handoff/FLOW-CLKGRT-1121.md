# FLOW-OBS-GCELL-1121 handoff 2026-11-21 (stood down at ~319k context; successor FLOW-OBS-GCELL-R2)
Class: DRT-0255 on a gcell that a reserved die-clock-site obstruction only partly covers (HEAD hd_host_e, hd_serdes sdr2c). FLOW-GRT-RESID scope taken over too (it stood down 04:01).

## Code (lane clone epyc8 /srv/opentallas-scratch2/claude/flow-obs-gcell-1121/repo, NOT PUSHED)
- e44fcd0731: first hook. b62f5f340c: full fix after the FABLE-PD-HEAD-0700 review (lanes/FABLE-PD-HEAD-0700.md section 2).
- tools/die_plan/obs_gcell_cap.tcl (new): set_global_routing_region_adjustment 1.0 on every gcell a source cuts ACROSS its tracks to < OT_OBS_GCELL_MIN_TRACKS (3) DRT-legal tracks. Sources: dbObstructions on M2-M7, excluding the ::ot_pgtt_obs temp guards, plus the OBS of placed block masters. Blockers: sources + PG-truth guards + PG swires. A track is free when its wire clears the blocker by the WIDTH-BASED spacing. A BTerm or macro pin exempts only the gcells it touches. Default on; OT_OBS_GCELL_CAP=0 turns it off. GRT-only, no DB change. Gcell grid 0.57 um, origin 0.
- grt_pre.tcl: the hook runs after pg_track_truth, before the appended PGCAP. grt_pg_replay.tcl replays it after TRACK_TRUTH, before PGCAP (default on, skipped when the kit has no helper). gen_phys.py copies the file into kits.
- tap_balance.tcl tb_seed_side: a tap port inside an M1 obstruction seeds its delay chain outside it, on the sink-centroid side, past OT_CLK_OBS_HALO_ROWS+1 rows (OT_TAP_SEED_SIDE=0 off). This is the sdr2d clk_t4/t5 straddle class. UNPROVEN: no CTS rerun yet.
- Tests: test_obs_gcell_cap.py (9), test_grt_pg_replay.py, test_rflow_defaults.py (test adjusted: the PG-truth-last rule allows the GRT-only obsgc hook after it). These pass in the clone. Remaining local failures are sparse-checkout FileNotFound only.
- Push: python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main from the clone, never --no-test, trailer "Co-Authored-By: Claude Opus 5.5".

## Why DRT fails on GRT-free tracks (measured)
asap7_tech_1x LEF M2-M7: SPACINGTABLE PRL gives 0.072 um next to any shape wider than 0.033, and DRT treats the obstruction as wide metal.
- host_e row y 345.99-346.56: no M6 PG there. 346.464 sits 38 nm from the edge (illegal), 346.528 sits 102 nm away (legal). GRT counts 2 tracks, DRT has 1.
- sdr2c 34.776: 42 nm from the edge. GRT counts 1, DRT has 0.

## Measurements
- host_e probe (4_cts, plain GRT 30 iterations): full hook cuts 23,756 of 173,964 partly covered gcells. Overflow 0, wirelength +0.1%. The baseline probe without the hook died GRT-0183.
- Signed QC sle_sc_v2 (has a macro, epyc2): 1,719 cut, overflow 0 on and off, wirelength +0.01%.
- Signed hd_ctl_e / hd_st_m / hd_st_str: no obstructions, GRT byte-identical.
- Proof v1 (first hook, no replay; epyc8 .../flow-obs-gcell-1121/host_e/hd_host_e, unit oth-ubuntu-2792729-1795271476, DONE): DRT-0255 gone, routed to the end. DRC 29, flat, all M7 at the u_epc macro top edge y 60.67: 26 Lef58EolKeepOut od[*] vs inst u_epc, 3 spacing to VDD/VSS. That is a NEW separate class (EPC macro M7 pin edge), not slivers. TT -66.49, FF -3.61.
- Exposure (static estimator, reserved_sites.tcl only, no PG/macro; scratch file expo.py; counts are sliver gcells / zero-legal gcells): qwen_kvsys 43 of 43 types exposed (kv3_pv* ~18-21k / 7-9k). s81_head 5 of 5: hd_lep0N 14,943 / 5,697, hd_serdes 10,241 / 5,187, hd_mesh 8,184 / 3,665, hd_host_w 3,555 / 1,049, hd_host_e 713 / 437. No S81, QC or HBM wave kit carries reserved route obstructions.

## Running units (leave running)
1. v2 proof hd_host_e with the full fix: epyc8 unit oth-ubuntu-3833325-1795274502. Kit /srv/opentallas-scratch2/claude/flow-obs-gcell-1121/host_e2/hd_host_e. Client log rtx-pro ~/flow-obs-gcell-1121-logs/host_e2_route.otrun.log.
   NEXT: check that tt_setup_repair_grt.log shows OT_GRT_PG_REPLAY restored ... OT_OBS_GCELL_CAP and an OT_OBS_GCELL line. Then read the route DRC: 0 DRT-0255 and the residual class. If there is no DRT-0255 and GRT overflow is 0, push b62f5f340c, post, and cc FABLE-FIX-HEAD-LEP0N (hd_lep0N is the most exposed HEAD type).
2. sdr2e lattice-snap A/B (inherited from OPUS-FIX-HEAD-SERDES-R4): epyc7 unit oth-ubuntu-3951418-1795264633. Log intel2 ~/opus-fix-head-serdes-r4-logs/sdr2e_route_e7.otrun.log. Evidence only: if DRT-0255 recurs, that confirms the snap does not cure the class. No relaunch.
3. sdr2d route (hold-only): epyc9 unit oth-ubuntu-3513796-1795271147. Read its DRC only, and let it finish.
4. Sweep: done (the numbers above). Raw output is in the scratch expo_*.tsv files.

## Open items
- After the push, file the EPC M7 pin-edge EOL class (host_e u_epc) with the HEAD owner or a flow lane.
- The tap seed-side fix needs a CTS A/B on sdr2d (4_cts input) to prove the +91..+112 ps capture insertion is gone. Also wanted: a GRT estimator line for *_tb* chain nets with guide length > 10x their HPWL (not done).
- Fable fix list item 5 (the route goal must not rewrite 4_cts.odb when 5_1_grt.odb exists; stamp 5_global_route.rpt PRE-REPAIR) is not started.
- Audit: core kits' core_final_repair.tcl / core_drv_repair.tcl do not source grt_pre. Core kits have no reserved sites, so this is likely moot.
