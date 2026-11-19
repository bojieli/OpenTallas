# FABLE-FLOW-1950: procedural and flow review (Fable, advisory, 11-18 19:43-19:55 PST)

Read-only review of 17:47-19:45 PST. Sources (intel2): autopilot/log.txt (6,631 lines in the window), kit_wave_state.json (saved 19:41),
autopilot/OWNERS.tsv, rt/current = fd8cedab6fa8 (all eight named fixes are ancestors), /etc/ot-heavy.conf + free + loadavg +
/var/tmp/ot-oom-age/kills.log on 6 hosts, lane posts. No new holds or gates are proposed (r703); host rails stay (r709). "Share" is an
estimate against about 1,200 job-hours (about 600 running jobs x 2 h).

## Headline
- S81 launches on D8e: 346 launches carry plan block df7446e48ba9 (53 at 17:55, 293 at 19:07), 0 on d8t. State 19:41: S81 333 RUNNING on
  D8e, 12 RUNNING on d8t. Window launches 401 (S81 346, QC 43, KV 9, HEAD 3). SIGNED 1 (s81 slice_station__t23).
- New and largest: no launch for 71 min (17:56 -> 19:06). A lane command (kit_wave.py cancel-rows --die s81 --item col_h9_r1__*,
  S81-DIE-R3) held kit_wave.lock from about 17:58 to 18:47; seven wave steps in a row logged "step skipped: another wave pass holds
  kit_wave.lock" (KW-STEP-TIMES total=0s). QC N4.1q was applied 18:18 and first launched 19:07. See class L.
- Memory: 5 infra-oom verdicts (was 47). Guard kills in the window: 3 (epyc8 2, last 18:52; epyc10 1 at 18:15; none on the other four).
  Available now: epyc10 803 GB, epyc8 579, intel1 479, epyc2 449, epyc7 311, epyc9 237. CPU is the overcommit now: epyc9 load 303 on
  96 threads, epyc2 234 on 128.
- Tick: 1379, 295, 369, 319, 223, 246, 205, 200, 1356, 1170, 566 s. The 200-370 s ticks are the lock-skipped ones (no wave step). Real
  ticks are 566-1379 s (wave step 275-1140 s; one orphan_sweep took 600 s). Not better than 1750 (median 773).

## Fixes verified
| Fix | State | Evidence |
|---|---|---|
| Old-block ENQUEUED retire (3c1d9b8e6f) | WORKS, but no RETIRE line | ENQUEUED rows not on the current plan sha: S81 49, QC 70, HEAD 11, KV 6. All 136 carry the block the item has in the current plan (same-block keep; 48 SWITCH-SUPERSEDE-KEEP lines). 0 old-block ENQUEUED rows remain on any die (S81 218 -> 49 kept, HEAD 12 -> 0 old-block). The three RETIRE-SUPERSEDED summary lines say "retired 0 ... stale ENQUEUED 0"; the rows left through CANCEL-SUPERSEDED (251) and the lane's cancel-rows (CANCEL-STOP 151, GRT-ARM CANCEL 66). The retire has no line of its own. |
| r711 DEFER-RESIGN (024e2a38d7) | PARTLY | 1 line only (s81_head hd_tile, 19:29). But 23 launches in the window are items whose OWNERS.tsv parent is SIGNED-UNVERSIONED (QC 18, S81 5) and 6 are SIGNED (S81 slice_station t22 / t25 / t31 ...). Some are the wanted unsigned classes of a split parent (slw_stm, slw_hc2); the rest need the per-class check. Not proven that no superseded-signed type launched. |
| SIGNED-UNVERSIONED select (206dfe4a14d1) | WORKS | QC slw_hc2 x2, slw_stm_v1 x2, slw_stm_v2 x2 launched 19:07:55-58 on N4.1q (b146b2d2b02a). |
| KV cell cap deleted (54d289d964a) | WORKS | hub_C, hub_Wo, pv_v1n, pv_v2n, pv_v3n (and pv_v3, hub_Wi) launched 19:06-19:07; 0 cell-cap FAILs after. |
| GRT hold zero-violator stop (f2c9d5f37f3) | IN RT, not exercised | No wave line shows it. PREGRT_HOLD_FALLBACK 10 lines, 4 rc 137 at 19:21-19:35 (col_h9 / col_h10). |
| signoff.py from rt (fd8cedab6f) | IN RT, not exercised | rt/current is this commit; the only SIGNED (18:30) predates it. |
| prd-* guard protection (fc3deb3d7c) | IN RT, cannot be judged | kills.log lines carry pid, comm and RSS, no unit name; all 3 kills are "openroad". "PLANGUARD" never appears in kills.log; the line reads "GUARD SIGKILL ... with a plan job running". |
| Plan-job admission charge (6ce34aa05e0c) | WORKS by outcome | Kills 3 (was 47 verdicts); all hosts above 23% available. |
| INV_PAST_PEAK_FACTOR hotfix | ALREADY RESTORED | 0.5 on all 6 hosts ("peak_gap hotfix 11-18 reverted after the code fix"); ot-heavy-reconcile links to rt/current on all 6. Nothing to do. |
| Replicate timeout + --tar | WORKS, late | QC N4.1q is on epyc2, intel1, epyc8, epyc9, epyc10. epyc7: tar -x running into .part, 38 of 58 GB at 19:47 (started 19:21), about 20 min left. QC gen_hosts (epyc9, epyc8, epyc2, intel1) do not include epyc7 or epyc10 yet. |
| S81 gen_hosts (1750 class A) | FIXED | RESTAGE-PICK lists epyc8, epyc10, intel1, epyc2, epyc9, epyc7. |
| QC plan probe (asked) | CLOSED one tick late | 18:52 "current plan blocks not probed yet"; 19:27 probed (213 blocks, SWITCH-SUPERSEDE-KEEP). The 70 QC rows are judged and kept as same-block. The 35 min wait was one long tick. |

## Classes

### L. A lane command holds the wave lock: 7 skipped steps, 71 min with no launch (new)
- Count: 1 event, 7 steps. Cause: cancel-rows keeps kit_wave.lock while it stops units and containers row by row over ssh (66 GRT-ARM
  CANCEL lines over 50 min, about 45 s per row). The wave step does not wait or share; it skips.
- Cost: 293 S81 D8e launches, 43 QC N4.1q launches and the 5 KV retries waited up to 70 min; the d8t rows being cancelled kept running
  meanwhile. Idle threads stayed low (0-37 of 624) until the queue drained (183 idle at 19:09).
- Structural fix (self-stopping): cancel-rows takes the lock only to mark the rows CANCELLED in state, releases it, then stops units
  outside the lock in per-host batches (one ssh per host). The wave step logs the lock owner's age, so a long hold is visible.
- Owner: WAVE-FLOW-R2. Share: about 5% (about 150 superseded jobs x 0.4 h), plus 70 min of launch latency on three dies.

### M. Cancelled rows are recorded as crashes: 175 infra-orphan verdicts (was 2)
- CLASSIFY CRASH (infra-orphan) 175, KIT-LOST 27, ORPHAN 126, ORPHAN-DEAD 11 ("resubmitted"), RECORDED -> structural.tsv 54. Nearly
  all are col_h9 / col_h10 d8t rows the lane had just cancelled: the unit is stopped first, the queue job stays open, the autopilot
  sees "client lost, kit logs idle 3 h" and files a crash.
- Cost: false failure records in structural.tsv and failure_breakdown, 11 resubmits of rows nobody wants, poll time.
- Fix: the cancel writes the queue job's terminal state (CANCELLED, reason) in the same state write as the row; the classifier
  returns early when the wave row is CANCELLED. Owner: WAVE-FLOW-R2. Share: under 1% compute; the failure tables are wrong by about 175 rows.

### N. Design failures labelled FLOW: 16 of 20 FLOW FAILs
- FLOW FAILs 20: kit_topology 8 (QC su_l1 "core chains carry unequal / zero depths [4, 5]": a latency design error), place 7
  (S81 serdes t13 / t16 OT_BOOT_RELEASE "expected 3 kept stages, found 0"; leaf t54 "NS face bank cannot fit within 30um pin
  retention"; eng t1, station t51, pvso_entry t1 / t2 KIT_PREFLIGHT / FAIL_PREFLOOR), kit_rtl 1 (leaf t56 rst_n "is not a bit of").
  Only src_manifest 5 is a real flow fault (d8t tree "is not main 3c913dbdfb23 + its overlay").
- Cause: kit_wave.py 3754 returns FLOW for every unmatched failure, and the "tool / Tcl error @place" rule catches the flow's own
  design checks (OT_* and "cannot fit" errors raised by global_place.tcl). FLOW is in PILOT_INFRA_CLASSES (12912), so these never
  count against the type and relaunch freely: leaf t54 cl501e5681 failed attempt 17 at 19:38 and launched attempt 18 at 19:41 with
  "unchanged fail key". Launch attempt numbers in the window: 1-2: 28, 3-4: 67, 5-9: 226, 10+: 80.
- Fix: the checks carry their class in the message (OT_<NAME> ... class=PLAN|RTL), set where the check is written; the classifier
  reads it. An unmatched failure gets UNCLASSIFIED (counted, reported), not FLOW. The existing 3x repeat stop then applies.
- Owner: WAVE-PILOT-FIX (classifier), TOOLS-DECOUPLE (class tag in the Tcl checks). Share: about 2% (20 fails plus the repeats).

### O. Misleading setup report: 5_global_route.rpt is FF only (COORD input, S81-GEOM-OPUS)
- The strip kits end GRT with CORNER=BC (hold repair), so 5_1_grt.log and 5_global_route.rpt load only the FF libraries; their
  report_wns / worst slack is FF setup at stock RC, not the TT setup the gate uses (-44.50 there, +27 at TT). FABLE-FIX-S81-STRIP
  found the same on 11-17 (t15 "kit GRT -17.6" was FF). Same class as the pre-tap-balance 4_cts_final.rpt.
- Tool readers in rt/current: one. tools/die_plan/legacy_gate.py grt_frames() (line 286) parses "worst slack max" / "tns max" from
  run/reports/*/*/base/5_global_route.rpt as kit_orfs and prints OT_GRT_FRAMES "kit ORFS read X ps, sign-off frame Y ps" with
  delta_ps = TT sign-off frame minus this FF number, with no corner named. tools/hbm_item9_collect_route_verdict.py globs every
  *.rpt in the reports dir. The wave gate itself does not read it (grt_policy_tt/ff.tcl is the sign-off session).
- Lane readers (posts that quote it): S81-GEOM-OPUS, FABLE-FIX-S81-STRIP, TL-QCSTBV1, WAVE-FLOW-R2; any lane that opens the kit's
  reports dir by hand.
- Fix: the GRT step writes the report as 5_global_route.<corner>.rpt and the first line names the libraries loaded; grt_frames
  reads the corner and prints it (and drops delta_ps when the corners differ). Lanes read setup from grt_policy.json. Apply the same
  rule to 4_cts_final.rpt (name carries "pre_tap_balance"). Owner: TOOLS-DECOUPLE (flow), WAVE-FLOW-R2 (legacy_gate). Share: 0%
  compute; wrong calls on near-miss types.

### A. Memory: 5 verdicts, falling (47 -> 5). 4 PREGRT_HOLD_FALLBACK rc 137 at 19:21-19:35 need a look by FLEET-OPS-R (no kills.log
line at that time, so likely the job's own limit). Share: under 1%.

### E. Tick: real ticks 566-1379 s, not improving. orphan_sweep 600 s and 91 s, plan_dies 22-326 s, collect 44-113 s,
launch_safe 112-122 s for about 340 launches. Fix unchanged (per-host batched probe with a time budget). Owner: WAVE-FLOW-R2.

### K. Smaller
- HUB-SYNC-FAILED since 18:00: lanes/OWNERS-SWEEP.tsv has a local edit in the hub checkout (14 alerts). Owner: the OWNERS-SWEEP writer.
- ARCHIVE FAILED 3054c87a89d6 (x20): probe rc 1 with a Traceback. Owner: FLEET-OPS-R.
- REAP-DEAD SILENT 70 lines, still report-only. 171 struct_stops in state (was 0 at 17:29): the stop is now written.
- Log noise: CELL-BIG 3,982 of 6,631 lines (60%).

## Do now (ranked)
1. WAVE-FLOW-R2: cancel-rows releases the lock before it stops units; the cancel closes the queue job (classes L, M).
2. WAVE-PILOT-FIX: unmatched failures are UNCLASSIFIED, design checks carry their class; leaf t54 is at attempt 18 (class N).
3. TOOLS-DECOUPLE + WAVE-FLOW-R2: corner in the GRT report name and in OT_GRT_FRAMES (class O).
4. QC-PLAN-R3 / TOOLS-DECOUPLE: add epyc7 and epyc10 to QC gen_hosts when the epyc7 copy lands (about 20:10).
5. WAVE-PILOT-FIX: per-class check of the 29 launches under SIGNED / SIGNED-UNVERSIONED parents; one RETIRE line per retired row (r711).
6. FLEET-OPS-R: unit name in kills.log lines so prd-* protection can be verified; CPU overcommit on epyc9 (load 3x threads).
