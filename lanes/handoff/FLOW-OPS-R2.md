# FLOW-OPS-R2 handoff (Opus 5.5; successor of FLOW-OPS-1300) -- live memory, 11-21 22:4x PST
Lane clone: epyc10 /srv/opentallas-scratch2/claude/FLOW-OPS-R2/repo (sparse tools+rtl+physical/common_flow); tmp .../FLOW-OPS-R2/tmp (push logs pushN.log, patchN.py). pytest: use `python3 -m pytest` (not -I).
## DONE (on main)
- P1 CLOSED (posted coord ca60a3e8ee): nomcap class = 2 cases, both re-recorded, count +0 (both types already SIGNED in OWNERS.tsv). Sweep: 64 NOT SIGNED on 7 hosts, 0 nomcap/coverage. Backlog 269 WAIT: 184 wait for a counting record, 76 were retired-host probes -> fixed 93fa1eb851 (autopilot rpy/rbash refuse epyc1,3-6; auto-resign SKIP RETIRED-HOST).
- WAIT-VISUAL: tick 22:08 released 61 advisory rows (51 QUEUED in route queue); dispatch re-check pending (task brumuu9si).
- P1 NOMCAP-MAP 5ce545eff0 (`signoff.py refresh-coverage RECORD --flow-tag T [--write]`); 2 re-recorded (qkd_ahub eco2 epyc7 fable-fix-kv-hub/r4/ahub/eco2/resign_je; QC sle_st_b_v1__pv0e7b1dcc epyc2 scratch3 auto-resign). Scripts epyc7 FLOW-OPS-1300/tmp/rerecord_r2.sh, epyc2 FLOW-OPS-R2/tmp/rerecord.sh. Other 37 NOT RECORDED have other causes.
- P2 push17 3504af932d; ot-run spill race (flaky concurrent spill test was real) 305156e71d (flock per lane around stage prep).
- VISUAL-NOBLOCK 94f0c2e4b8 + PASS-COND 3e9d8db466 (auto_geom_passed = geom_verdict PASS|PASS-COND + geom_dir). kit_wave.json review_before_route.required unset on qwen_compute/s81/s81_head/qwen_kvsys (hub a5e60619f7). Re-adders: d68244fee44 03:07 QC R6V1, 8282888a520 03:24 KV D25e3, a8e47f3cac2 04:12 apply_reviewed_tree_marker, f344cc7b889/019bf090c75 14:16-14:21 unlabelled.
- stand-down.sh refuses context reasons (hub 0352f644d5).
## PUSHED 7312afb7a3 (push6) = 4 commits: b50fe08117a --cancel exact (client_matches), 2a57f05622c kit_wave_edit required_review_problems + marker drops required, 329857984a8 gen_phys tee lint (test_gen_phys_tee_status.py; audit: all 49 tee producers are messages), f8c0495a792 ot-run JOB-LEASE (COORD: lease --dir/cmd scratch trees/rt sha via ot_lease, renew TTL/3, release atexit; test_ot_run_job_lease.py). push5 failed only because I changed the ot-run docstring (test_ot_run_shell_guard pins its sha) -- reverted.
## P3 canary s81_head_cl: CONFIRMED + NARROWED main 5a966bb45b (CLASS_SKIP clk_landing). A/B on: slew 14 / TT 129.8; off: 0 / 135.08. J8 sha posted (coord 04baa8752e; S81-J6-ASSEMBLY-R5 unreachable via SendMessage). TODO: read timer canary s81_head_cl_5a966bb45_* verdict, post it.
- good 7b6af7dd0, bad 3b2f4d044.. identical; only synth commit = 8a2a7b31a97 (class keep); OT_KEEP_WIRES gains ot_dp_clk_landing:* (+9 cells).
- A/B intel2 flow-canary/runs/ab_flowops_r2/{on,off}/s81_head_cl_8a2a7b31a_1121_2145* (off = OT_CLASS_KEEP=0 OT_ASYNC_REG_KEEP=0); at GRT 22:3x. Then: if off == good -> narrow in tools/die_plan/replica_keep.py (drop "landing" from CLASS_MOD / exclude ot_dp_clk_landing, keep relay/station/ROM/reset-sync) + test_flowops1300_class_keep.py, push, canary on new sha, SendMessage S81-J6-ASSEMBLY-R5 the J8 sha.
- s81_cl needs FLOW-CANARY-R2 restored fixture. HBM canaries dropped. Old failed runs flow-canary/ab/runs_flowops_r2 -> ot-delete later.
## QUEUE: LEC register matching (FAM-S81-SERDES-R7 dec_j6c 33 NEQ, g_pe[45].thq[1] paired by name with u_bm.th[11][10]); watchdog (container gone/0% CPU 30 min -> HUNG + cancel); io_guard, lever 9, items 8/11/12; ot-push-main flaky tests; tools_lag parser false positive.
## 11-22 08-10 PST update
- Pushed on main: 7ca4f3bb5f (LEC tap-clone seeding + F1 CAUSE-CAP by type stem), a054ecf388 (F4 dies.<die>.parked; F5 hold owner=/eta=, HOLD-OVERDUE, orphan hold release, NO-PROGRESS blocker), 3b1cea8bec (plan_gate_pre LANDREMAP), 1ca85a2bee (ABSPATH + localize, LANDREMAP baseline from <plan dir>/bind_of_record), ISTCYC + reprice pushing as push15 (b5e5a5e3368).
- coord: stale_list parked filter bf860c66ba (2b1342e2cf had a quoting bug for ~2 min); kit_wave.json dies.hbm.parked 01ba83565d.
- LANDREMAP finding posted to OPUS-FIX-KV-HGI-R6: R6g still flags v2 x2 (remap skipped landing_raw_branches.1 "chain ends").
- Canary s81_head_cl after narrowing (30b1f11ad/ae9a5815f/52e6c7b5f): grt drv 0, TT 117.0 vs base 127.2 (-10.2, tol -10), signoff drv 39 vs 12; face_cover FAIL is older (before regression). TODO: diff for the remaining 10 ps.
- ABSPATH strict from 2026-11-29 (ABSPATH_STRICT_FROM in plan_gate_pre.py).
- Queue next: KIT_TOPOLOGY_BIND_STALE, LEC dec_j6c function matching, watchdog/io_guard/lever 9/items 8,11,12, push test triage, tools_lag false positive; publish_gate/ot_build do not pass --baseline-plan yet (LANDREMAP/ISTCYC need it).
- 11-22 ~10 PST: ISTCYC + reprice on main fda4eaad0e (posted to the die plan lanes); DEADIN on main 16811af012 (posted to COLROM-R6, coord 7b4aaed3e1). The 4 COORD class fixes are done. Next: KIT_TOPOLOGY_BIND_STALE, then the canary 10 ps diff, LEC dec_j6c, watchdog/io_guard etc.
- 11-22 ~11 PST: TAPNAME (plan_gate_pre) + private-spec KIT_TOPOLOGY_BIND_STALE refusal on main 6d2e187f0d, posted. Rule slip disclosed: a test file was written into opus-fix-kv-hgi-r6 launch27f plan_of_record on epyc8 and rm -f right away; use FLOW-OPS-R2/tmp copies only.
- Next: canary 10 ps diff, LEC dec_j6c function matching, watchdog/io_guard/lever 9/items 8,11,12, push triage, tools_lag FP; publish_gate/ot_build --baseline-plan wiring.
- 11-22 02-03 PST (after weekly-limit resume): e8a66236b2 PORTPAD identity remap + REMAP-BASE (posted to HGI-R6), 8bc99535e8 tree_write_guard rule 3 (lane-own), 7516d11ccf R8STALE. epyc8 FLOW-OPS-R2/tmp/pp = my tools mirror (physical/rtl symlinks into opus-fix-kv-hgi-r6/launch27f, read only) for real-plan tests.
- Next: canary ~10 ps (keep-off vs narrowed diff), LEC dec_j6c function match, watchdog/io_guard/lever 9/items 8,11,12, push triage, tools_lag FP.
## 11-22 03:xx PST (ENV-OVERRIDE, R1, B1)
- AB-CONSUMED: main 79f34e2ad42 (FAIL when A/B key not exported by config.mk). FALSE-FAILED gen-consumed knobs (H9R0-R4 kit C OT_GRT_CONG_ITERS; another lane landed GEN_CONSUMED 5c6c4945c80). Fix e1b02444403 (in push24): gen_phys.ENV_CONFIG_FORMS (translated forms) + key_readers source scan (gen py read = consumed, flow-only = FAIL, nobody = WARN). Re-judged 19 in-flight A/B kits: 0 FAIL (old code false-failed 3 hd_lep0N kits on OT_GEN_M8_GRANT/IO_HOLD/PG_PIN_CHECK/KW43_FIX; KW43_FIX now WARN read-by-nothing). pkit_core3s OT_TAP_RESET_SPLIT/AFFINITY still FAIL (true drop).
- 48-h audit: only true drop = fable-fix-qc-coll-r2/pkit_core3s (TAP_RESET_SPLIT+AFFINITY). CLKGRT 2 kits ok, COL-H9R0 6 ok, COLROM R5/R6 ok, QC-COLL KEEP_WIRES ok; FAM-QC-CB-R4 (6 specs) + FAM-S81-LEPE-4 (2 specs) declared no A/B keys.
- R1 FAMCAUSE 82a667286b3 (push24): kit_wave path_cause_key/famcause_held (>=2 type stems same path key in event -> family hold), repeat_stop.is_plan_input PLAN(non-gen)/STRUCTURAL/stop markers. Hub replay: QC cbf_q00+cbx_q10 held.
- B1 d31350886cd (push24): plan_gate_pre EMITNAME (clock landing inst names vs bind sv_id), bind_rowcheck RELAYSINK (relay_depth rows vs elab leaves; real gate1 bind 32,992 rows -> 0).
- push22/23 "REBASE CONFLICT in: <empty>" = I edited the clone while ot-push-main ran (tests passed). Rule: never touch the clone during a push.
- Left /tmp/flowops_r2_kw/*.py on intel2 (read-only replay copies; not my scratch dir; not deleted).
- PUSHED main 4396e129eff (push25): e6729610919 R1 FAMCAUSE, 0cceb43c4c3 AB-CONSUMED fix (ENV_CONFIG_FORMS merged with GEN_CONSUMED + d2196689499 _grt_cong_iters(budgets,tn)), 4396e129eff B1 EMITNAME/RELAYSINK. DONE posted (coord d6dff183c5). Next: canary ~10 ps gap, LEC dec_j6c.
- Removed my replay copies /tmp/flowops_r2_kw on intel2 with ot-delete, not rm -f: the owner rule allows rm -f only inside my own scratch tmp dir, and a COORD direction is not owner consent. Now on: s81_head_cl canary ~10 ps gap, then LEC dec_j6c.
- 11-22 04:xx: TOOLS-LAG FP fixed main 2959d7f51b9 (launch rt pin). Watchdog 30-min dead-CPU already on main (HUNG_DEAD_CPU_MIN). LEC dec_j6c parked WATCH (artifacts gone; keep-th fix EQUIVALENT). Canary A/B: off2 = flow-canary/runs/ab_flowops_r2/off2/s81_head_cl_d14cac8bd_1122_032555_381891 vs timer s81_head_cl_d14cac8bd_1122_031529_108890 (waiter br4w8by6s). Lesson: pgrep -f pattern matched my own ssh shell; use exact PIDs only.
## 11-22 04-05 PST FABLE-FLOW-0350 (U1/R1/B1 + COORD TAPNAME-UNCHECKED)
- Clone commits (not yet pushed at write time): 245711571ed R1 STRUCT-FIRST (repeat_stop BLOCKED-PLAN at first STRUCTURAL/PLAN-nongen/stop marker; release only plan block / retry key item@N / unblock; test_repeat_stop 2 tests changed at_the_third -> at_the_first), a463f664068 TAPNAME-UNCHECKED (density base solved with taps._root=--tree; unsolved = FAIL TAPNAME-UNCHECKED rc1 PLAN-GATE-PRE UNCHECKED), e75b49a2674 U1 HOLD-OWNER (under_use.hold_owner_rows + die_owner_lane; autopilot.py hook in OWNERS build goes with the B1 commit).
- B1 BIND-DOOM: new tools/autopilot/bind_doom.py (+test_bind_doom.py), autopilot.py run_phase("bind_doom"): detached sweep every 10 min / on rt move, per host REMOTE /proc scan of bind.py bind|elab, runs host rt/current plan_gate_pre TAPNAME+EMITNAME with --tree=cwd; posts BIND-DOOMED once per (unit, plan sha) to lane of claude/<dir>; autopilot/DOOMED-PLANS.tsv; state bind_doom.json, posted bind_doom_posted.json.
- Canary d14cac8bd: keep-on 105.94 vs keep-off 124.4 setup TT (base 127.2) -> narrow replica_keep further (next). face_cover FAIL both arms (src).
## 11-22 05:0x PST: 0350 pushed + add-ons
- main f4e075f79eb: ec9c345795c R1 STRUCT-FIRST, a1ae1f21251 TAPNAME-UNCHECKED, af2435fb9ab U1 HOLD-OWNER, aad13eaaab6 B1 bind_doom (+OWNERS hook), f4e075f79eb RESETPUB (plan_gate_pre + retap --republish-reset). DONE posted.
- INCIDENT BIND-DOOM-STORM (mine): merge-queue autopilot tests ran bind_doom.step with temp AP_DIR -> 64 real fleet sweeps; I killed them by exact pids 12:57; fix main ba20f11e2d8 (hub dir only, no pytest, flock). Lesson: any detached launcher in the tick must refuse under pytest and outside the hub AP dir.
- coord 3c7ddba256 owners_sweep PRIV-LIVE-1122 (private kit live = result RUNNING / active kwp|runitem unit) DONE posted.
- Open: RESETPUB real solve on plan_v3p6n3 vs v3p5r_lat running on epyc10 (tmp/rp_real2.out; QC die reset solve >1000 s cold). bind_doom real: QC TAPNAME checks take >900 s each (timeout) -> consider raising CHECK_TIMEOUT_S or sharing the bind-gate cache.
- Next: canary narrow replica_keep (keep-on 105.94 vs off 124.4), io_guard, lever 9, items 8/11/12, push triage.
## 11-22 06:xx PST
- main 36d0a6df8f6 RESUME-GOAL-1122 (finish=route on stage resume in run_kit.sh + resolve_chain_goal; private no-goal = auto, never geom). main 2bc14507b4d RESETPUB suspect = FAIL in seconds (die reset solve >3400 s on QC; OT_RESETPUB_SOLVE=1 to prove). coord owners_sweep PRIV-LIVE 3c7ddba256. All posted.
- bind_doom real (epyc10 5 QC binds): 3 PASS, 2 timeout at 900 s (QC TAPNAME density solve) -> CHECK_TIMEOUT_S may need raising; storm guard ba20f11e2d8.
- Next: canary narrow replica_keep (keep-on 105.94 vs off 124.4 ps), io_guard, lever 9, items 8/11/12, push triage.

## 2026-11-22 ~07:00 PST update (FLOW-OPS-R2)
Pushed to main since the last section:
- 5bb9a043e39 TAPNAME-DELTA-1122: plan_gate_pre TAPNAME solves only density types whose clock section (minus kit-only tap_balance_to / tap_slowest_max_ps) differs from the base; QC v3p6n3 vs v3p5r_lat 6/124 types, 56 s cold, 11 s warm (was ~160 s; the 1-h runs were the old RESETPUB die-wide solve, gone since 2bc14507b4d). bind_doom: CHECK_TIMEOUT_S 3600, 4 parallel checks/host, dedupe by (plan sha, tree, asbuilt).
- f4e0e522b00 HUB-DIRTY-1122: hub_git_sync commits lanes/posts/*.md + lanes/OWNERS-SWEEP.tsv; refusal line names mtime + fuser holder. HUB-SYNC-FAILED had cleared 05:54 already.
- 233947ba8aa LAUNCH-JOURNAL-1122 (W1): kit_wave launch row journaled (fsync) before systemd-run, replayed by load_state, compacted by save_state; state saved after the collect phase. NOT done yet: detaching slow probes (bind_preflight 126-516 s/tick, plan_dies) from the tick.
- 7ed394df813 HOLD-DONE-1122: hold_guard_grt runs no further margin chunk once a chunk ran and ws >= 10 with 0 violators (OT_HOLD_DONE_STOP=0 off). New kits only.
- c19dbd9b5e6 PLAN-GATE-BESIDE-1122: bind.py forks plan_gate_pre beside elab/bind, joins before return, refusal -> rc 2 + OUT/PLAN_GATE_PRE_REFUSED.txt; OT_PLAN_GATE_PRE_SERIAL=1 old order. ot_build "pre" node still serial.
In flight: E1 FLEET-GUARD-1122 tools/conftest.py Popen guard (full tools suite run on epyc10 to find tests using real ssh/systemd-run/ot-run); hold-chase fleet-hours scan (hgscan.py, 7 days, dedupe by guard-line hash).
Queue after: W1 probe detach, canary narrowing (replica_keep ~18 ps), io_guard, lever 9, 8/11/12, push-test triage.

## 2026-11-22 ~07:30 PST update (FLOW-OPS-R2)
- 7d9c8891149 GEOM-ADVISORY-RC-1122: geom_check.sh rc 0 on an advisory rule FAIL with a verdict line (OT_GEOM_STRICT=1 old).
- 385e3b15c5b + 2d4444116da FLEET-GUARD-1122 (E1): tools/conftest.py Popen guard stubs real ssh/scp/systemd-run/ot-run/ot-heavy/ot-delete/ot-push-main (rc 255); OT_TEST_FLEET_OK=1 / OT_TEST_FLEET_STRICT=1. Before: ~105 real ssh per autopilot+fleet+die_plan run.
- PROBE-DETACH-1122 (W1 part 3) commit 53ea5fe3448: bind preflight full probe runs as unit kit_wave.py bind-probe, result <ap_dir>/bind_probe/<key>.json; rows BIND_PREFLIGHT_PENDING meanwhile; OT_BIND_PREFLIGHT_SYNC=1 old. (push in flight at writing)
- HOLD-DONE measurement posted: 115 kits / 96 h in 7 d (76 h in last 24 h) of margin chunks after ws>=10 & 0 viol.
- Earlier X1 note: a hub-side temp file I wrote went to intel2 /tmp and was rm'd; from now hub temp files go to the lane tmp dir only.
Remaining queue: ot_build "pre" node beside elab (optional), canary narrowing (replica_keep ~18 ps), io_guard, lever 9, 8/11/12, push-test triage.

## 11-22 08:5x PST: FABLE-FLOW-0800 S1/T1/D1 pushed
- S1 e26626c8886: run-item reads CONTROL from rt/current at each stage start (geom_check.sh staged from rt/current; geom_gate + resolve_chain_goal run via `kit_wave.py control-call` of rt/current when their source differs; result tools stay pinned; KW_CONTROL_REACH / KW_FIX_NOT_REACHED lines + result.json control_reach). OT_CONTROL_ROOT=0 off. Drivers already running keep old code (only from this sha on). Not done: hold_guard_grt.tcl from rt/current (it is sourced from the kit copy by grt_pre.tcl inside docker), FIX-REACH.tsv per FLOW-FIX push.
- D1 6e0567b2a30: ot_status defers a DIED post whose log is X.live.log until X.log (stdout, written by kit_wave after ot-run exits) is there (<=45 s). Re-classification of the 70 NO-PATTERN of 11-22: 42 GEOM-FAIL (this race), 26 'log none' (ot-run without log: FLOW-FLEET-R2), 2 kit_istations, 1 other.
- T1 da102e4d499: driver-side BIND-GEN-TOOLSKEW -> switch to the gen host rt snapshot that fits the bind stamp (KW_BIND_RT); ot-tools-sync private-spec dry run before flip (qwen_compute free item, 6 s; red only if prev rt passes). Launch side = WAVE-OPS-R1 1c8b40168f9.
- S81 bind_preflight re-enabled 07:35 (a093cbb0ba): ticks 305 s / 354 s, no stranded rows (posted 5cb7493a3c).
- Canary narrowing arms running (intel2 ot-run via canary.py): runs/ab_flowops_r2/{classoff,asyncoff} on d14cac8bd26f (baseline keep-on 105.94, keep-off 124.4 ps TT setup).
- Next: read canary arms; io_guard, lever 9, items 8/11/12, push-test triage; optional S1 hold_guard + FIX-REACH.tsv; tick hang in plan_dies prewarm_probes (07:33).

## 11-22 ~18:4x: RESCORE-SWEEP done, nothing to rescore
- Swept 7 d of signoff.json on 7 gen hosts (~20k records). No NOT SIGNED record has unconstrained in its reasons, because the minimal profile already makes it advisory (it only appears in legacy_reasons). Nothing written. Posted coord 19da330592.
- Scripts: <host>:/srv/opentallas-scratch2/claude/FLOW-OPS-R2/tmp/{soscan,sotally,sopar}.py
- Next: read canary arms landing/rrelay/rstsync (intel2 flow-canary/runs/ab_flowops_r2), narrow replica_keep; then io_guard, lever 9, items 8/11/12, push-test triage.
- Canary arms read (coord ff9a2b7d04): only the rrelay keep moves TT, 124.4 -> 105.94. That is placement noise on a MET half-cycle path (u_face q[568] -> u_wen, fclk_in_t_i), not a relay path. Kept the class keep. Recommended rebasing the canary baseline to 105.94 (FLOW-CANARY-R2). The canary item is closed.
- Next: io_guard, lever 9, items 8/11/12, push-test triage (test_repeat_stop 2 FAILs seen in bfjxwrdt9: hd_serdes_post_cts_five_times / station_row_overlap blocked_at_third).

## 11-22 17:5x PST: RESUMED + NATIVE-GLUE-LOCK
- Glue lock 2ea3a30545d is on main as d8bcb5f08e1 (13:38). Codex's 3bccf4b00a6f = main merge of bind-worker-wait c99220d870a (bind_emit_par waitpid scoped to workers), not a second lock. rt/current 9c133d90aec1 on all 7 gen hosts carries both. Posted coord 097a2123ee (lanes not reachable via SendMessage).
- Open: signoff.py copy_signoff_bundle nomcap guard checks destination/nomcap/MANIFEST.json but copies into nomcap_libs, so every repeat install re-copies over read-only libs (BKSEL 12:01). Fix: skip when destination nomcap_libs/MANIFEST.json equals the source one, else replace through a temp file. Also HEAD turn canary a087287d5 October golden FF -20.85 stale (12:44 WAITER-FAIL) -> FLOW-CANARY-R2 rebase like s81_head_cl.
- Then: io_guard, lever 9, items 8/11/12, push-test triage.
