# FAM-S81-SLICE handoff (Sonnet 5.5, 11-21 ~06:30 PST; successor FAM-S81-SLICE-R2)
Family: S81 slice types (slice_station t*, dsdv_slice_c1x_C / iq_C ...). Rep: slice_station__t36. Work root epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice (call it $W).

## Live units (all epyc10 under ot-run, OT_LANE=FAM-S81-SLICE; I hold local run_in_background pollers that die with this session: re-arm)
- t36 private proof on J6 candidate C1n (gate green: bind 0, LATCHECK ok, G0 87 inherited / 0 new, PRE pass; C1n = monitor-home, NO FSTART): unit oth-ubuntu-344587-1795255611, kit $W/t36_c1n/gen/slice_station__t36, log $W/t36_run.log. Normal priority (ot-run refuses --priority plan for kits; never OT_RUN_PLAN_OK). Was in CTS: 287k nontap cells (85.6% of cap). Read POST-hook OT_CTS_POST_TIMING only, then final GRT overflow. Expect monitor ring (-724) fixed; a START-broadcast path may remain (FSTART is in C3g/C3i only).
- c1x_C per-type yosys census, 6 jobs t6,t10,t1,t5,t7,t8: $W/census/t*/{stats.json,otrun.log}; script $W/census_run.sh + $W/mkys.py. Not admitted yet at last check (memory queue). t3,t4 have no J5 kit gen. Codex's t9 census (unit 2354952, done): epyc9 fable-fix-s81-slicec/t9_hier_census_1121/stats.json.
- xs4_equiv bench, 2 jobs (client PIDs 3455439 / 3455440, queued for memory): $W/bench_wreg.log (define ON, every legal case must PASS) and $W/bench_base.log (define off, baseline); out dirs $W/bench_wreg, $W/bench_base; script tools/s81_slice/xs4_equiv.sh in the clone.

## RTL (committed in the clone, NOT pushed)
- Clone: $W/clone, branch claude/fam-s81-slice-wreg-1121, commit 4f03fa6cea (sparse cone tools, rtl, physical/die_plan/s81, results/rtl/dsrom_recovery_20261004, physical/asap7_memory_macros_v2; base main 39d243610b).
- Diff: rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv, define OT_S81SL_XS4_WREG (default off = previous form bit for bit): registers we/wa/wd/mask of the 24 x-buffer macros (u_mem, g_w/g_m) and ew/ea/ed of the 6 exponent macros (u_em) once at the macro pins. tools/s81_slice/xs4_equiv.sh: new `wreg` mode.
- OPEN RISK: the write lands one edge after the arrival-table valid. If bench_wreg shows mismatches, add the matching +1 on the arrival tables / read side and declare +1 latency (update the bench model by +1); do NOT push until bench_wreg PASS (or the +1 model passes) AND an equivalence proof vs define-off (LEC or the bench).
- Then: python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main (never --no-test), post define name OT_S81SL_XS4_WREG + sha to S81-J6-ASSEMBLY-R2 for J7, then private t9 kit with the define on (src_manifest tree for sign-off, or off for proof) to post-hook CTS and GRT; target gd_b->u_mem/wd_i 2,113 paths.
- xfin delivery stage: ALREADY ON MAIN, no new RTL. ot_s81dv_xfin parameter DLV=1 is the default (OPUS-FIX-S81-SLICEC, 05113f6669); J5 and C1n asbuilt.json both contain it (g_dlv_e 960, g_dlv_n 288). The 1,603 xf dl_d/id -> f_d paths I measured came from the old D8h-tree p1 kit. Confirm in a C1n c1x_C kit.

## c1x_C findings and J7 package
- File lanes/handoff/FAM-S81-SLICE-J7-c1xC-rows.json v1.2 (+ FAM-S81-SLICE-J7-c1xC.md). Sizing: t9 place 480,720 nontap (+121k tap), t3 477k, t6 503k at CTS (setup -1572, old plan). Census: xg (xs4 172.6k + rstopt_xo 51.4k generic) ~178k mapped, landing/station infra ~150k mapped. Split B: strip (S/W/N/E perimeter bands, ~150k, registered chains, +0 cycles) vs core+xg body (~185k; t6 body ~353k, t9 ~331k, under cap). xs4|rstopt_xo cut specified (S-XG1) but not needed. Strip/body partition_types = J7 design work for S81-J6-ASSEMBLY-R2 (open: W band vs core origins, sub-tile schema).
- Plan level is clean: istation_respace --limit 405 on C1n gives 0 rows for all c1x_C / iq_C (max hop 397.6; iq_C t1 one 416.1); relay_depth rows already aligned (eg_c/eg_d/eg_v equal D; the D1/D2 mismatch was plan_j3b only). Failing hops are soft flop -> core pin (placed): gd_b->u_mem/wd_i, xf dl_d->f_d, relay->xr lo_d, xg.u_r g_d->xr dl_e: hence the RTL stage above.
- c1x_C t6 attempt_46 (old plan 3fa87b84b18, epyc10 5_1_grt 17.8 h, setup_ws -1572): meets the >3 h unable-to-sign rule; DIE-R5's row, I did not cancel; COORD decides.
- My scratch tree s81-j6/candC1nX + gates/candC1nX (plan unchanged, gate cancelled): delete via ot-delete when idle.
- C3g/C3i gates failed at bind (HARD_CORE_PARAM_ALL, svc prov_1119 config.mk unreachable): escalated to S81-J6-ASSEMBLY-R2.
- slice_station hold<=30 DBs: redundant (signed on other plans), HARVEST-ECO-2350 owns. t52 Tcl scope crash fixed on main 5294e088f55 (regenerate only on fresh tree).

## Next for R2
1. Read t36 post-hook CTS/GRT; post. 2. Read bench_wreg/base; fix hazard or push. 3. Read census t6 etc; confirm strip ~150k per type. 4. t9 define-on kit. 5. Hand J7 define+sha.
