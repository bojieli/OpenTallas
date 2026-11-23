# FIX-QC-DPL-RERUN handoff (Opus; started 11-23 03:3x PST by FIX-LEDGER acd269758d3b62a53 for ledger x5)
Item x5: QC st_a DPL-0033 after repair on clf4365a62, pvd2ec7769, pv4242de79, pv88773f93. Done = 4/4 show 0 DPL-0033 past the post-repair DPL. Wanted 12:00.

## Facts
- rt/current 4737f2eea2fd (03:3x) and rt 0d6ca1628921 both contain f60d28bf6dc (merge-base check on intel2). grt183_make.sh in 0d6c differs from the V2 kits' copy ONLY by the GRT-DPL-DIAMOND hunk.
- Coverage of post-repair DPL (read stock global_route.tcl in openroad/orfs:asap7lock and asap7lock-grtT1): erase_non_stage_variables grt is top-level line 3; post-repair `log_cmd detailed_placement` at lines 88 (after repair_design) and 108 (after repair_timing, then check_placement 109) sit inside procs called later. The patch inserts the wrapper before line 3 and renames ::detailed_placement globally, so both post-repair calls go through it. COVERED.
- The failing V2 runs (e.g. clf4365a62 5_1_grt.log 11-23 00:25) predate the fix: their route-stage flow refresh was 11-22 13:16 PST (rt 9959118207e3 / admission_tools), kit grt183_make.sh 11-22 15:43 had 0 OT_GRT_DPL_ARGS lines; log shows "Legalizing using negotiation legalizer", DPL-0701 53 left, DPL-0033 at global_route.tcl:196.

## Track A (launched 03:5x): V2 GRT-only reruns, same plan + config.mk (diff identical), 4_cts.odb of the failing wave kit
- Kit copies: <host>:/srv/opentallas-scratch2/claude/FIX-QC-DPL-RERUN/kits/<type> = kit_fork + results/logs/reports through CTS + missing inputs from source; grt183_make.sh from rt 0d6ca1628921; resume.json (auto:false) start=grt; lec_async.on/identity renamed *.off_probe (no LEC).
- Runner: kits/run_kit.sh (copy of the wave gen/run_kit.sh) KIT grt 24 8, through ot-run --mem 24 --threads 8, OT_LANE=FIX-QC-DPL-RERUN.
- epyc7: clf4365a62 (ot-run pid 2079714), pvd2ec7769 (2079715), pv4242de79 (2079716); epyc2: pv88773f93 (1156183). Logs: kits/../tmp/otrun_<type>.log, kit run_grt.log, run/logs/asap7/*/base/5_1_grt.log.
- 03:5x all four queued on ot-heavy CPU_CHARGE (fleet saturated, 17 waiters on epyc7).
- Read per kit: grep -c DPL-0033, OT_GRT_DPL_ARGS lines, DPL-0701 residual, post-repair setup/hold wns (5_1_grt.log report_worst_slack / OT_HOLD_GUARD_GRT lines).

## Track B (V4): c3n (plan eecec2f6206b, rt 0d6c) binding on epyc8 /srv/opentallas-scratch2/claude/fable-fix-qc-v4/c3n_bound (03:5x). Ruling: when bound, private-spec --goal grt on c3n for 2 reps (slw_st_a_v2 clf4365a62, sle_st_a_v2 pvd2ec7769); full gen->GRT ETA ~9 h, so it is follow-up evidence, not the 12:00 answer.
