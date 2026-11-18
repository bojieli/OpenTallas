# FABLE-FLOW-1555: procedural and flow failure review (Fable, advisory, 11-18 15:43-15:58 PST)

Read-only review of 13:45-15:45 PST. Sources (intel2): autopilot/log.txt (3,861 lines in the window), autopilot/state.json, kit_wave.json,
kit_wave_state.json, tick_hosts.tsv, lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py, `ot-run --status`, lane posts, rt/current code
(696107ba1a44), /var/tmp/ot-oom-age/kills.log on 6 hosts, and 4 kit directories on epyc8/9/10. No new holds or gates are proposed (r703);
host rails stay (r709). Counts are measured. "Share" is my estimate against about 1,230 job-hours (about 615 running jobs x 2 h).

## Headline
- Wave FAILs 71 (37 in the 1400 window): INFRA 26, FLOW place 16, PLAN place 15, kit_topology 10, other 4. Autopilot verdicts 101: memory kill 41,
  orphan 16, cancelled 24, post-CTS stop 8, GRT overflow 3, routed-not-signed 4, SIGNED 1 (hd_st_str, logged SIGNED-UNVERSIONED).
- Launches 112 (25 / 53 / 34 by hour), stage SUBMITs 132. BIND-STALE 0, LAUNCH-HELD 0, REFUSED 0, ENOSPC 0, stale-copy 0.
- Tick got 3x slower: 558, 1626, 1602, 1298, 828, 472 s (median 521 s at 1400). Only 3 ticks ran between 13:51 and 15:11.
- The main loss is memory overcommit on epyc10 / epyc8 while epyc7 and epyc9 hold 642 + 381 GB available (class A).
- Two routed near-miss results were deleted in the window before the keep fix landed (class B); the late ECO still does not run (class C).
- Three of the ten fixes are not in effect: struct stops (tool landed, 0 stops placed), the publish_apply bind_matches self-check (not in
  the code), late ECO (the fix cannot reach kits admitted before it).

## Did the fixes take?
| fix | verdict |
|---|---|
| env hash e441a4dcd7 | TOOK. RELAUNCH-ON-FIX 8 (54 at 1400). Unnamed "changed env" 5, all in ticks that started before 14:02. After that 1 line, with the key named: col_h9_r1 pv11c696bc "env keys: OT_GRT_TRANSITION_MODE" (the wave's own GRT-EDGE auto edit, see class D). The 4 su_l1 QC types failed twice more each (hash format v2 re-arms each key once) and are SKIP-SAME-INPUT again at 15:35. |
| retry lists deleted | DONE. Live `retry` keys: s81 2, hbm 3, others 0 (683 at 1400). RETRY-IGNORED 10 lines: lanes still add keys that name an old attempt. |
| struct-stop / cancel-rows 1cf3aa0acc | NOT USED. state struct_stops = 0 entries, 0 STRUCT-STOP log lines. col_h9_r1 on d8t: 23 RUNNING + 37 ENQUEUED (34 + 26 at 1400), launched again 14:15 and 15:22. col_h9_r2: 8 + 50, launched 14:15 and 14:43. cbx_q10: 3 + 1, launched 15:23. The S81-COL-FLOW hold was dropped at 14:03 "replaced by struct-stop", and the stop was never placed. |
| publish_apply bind_matches self-check | NOT LANDED. rt/current publish_apply.py has no bind_matches / kit_topology call; its last commit is c922a2a40a4 (05:20). No BIND-STALE in the window, so untested either way. |
| late-ECO seed keep 8f3d1679753 | NOT EFFECTIVE YET. 4 late ECOs in the window (13:53, 14:23 x2, 14:56), all "prd_mk.sh failed (pass dir not staged)" in 1.5-10 s, 0 ran. See class C. |
| PROBE_DELETE routed keep cc35e3cf61 | LANDED 15:35, UNPROVEN: no routed verdict since. Before it: slice_station__t47 a7 (TT -4.44, FF -12.54) deleted 14:06, hd_ctl a2 deleted 14:58; sle_hc0 cl38badc56 a2 and cl4baa7c9c a4 survive on epyc9 only because a container still mounted the kit (6_final.odb / .spef present, checked). |
| DRT-0255 FAIL_route 9e123f310b4 | LANDED 15:10, NOT EXERCISED: 0 DRT-NOPATH / FAIL_route lines; only kits generated after it carry the new run_kit.sh. |
| GRT port-hold opt-in 1fd8080739a | LANDED 15:27, in rt from 15:31. NOT EXERCISED: wave units started 15:34-15:35 still ran rt 1a2846af933f, which lacks it. |
| kit_wave.json CAS 696107ba1a4 | LANDED 15:41. HUB-SYNC-FAILED ran 14:20-15:39 (9 alerts) and CONFIG-DRIFT 33 min, from the 14:09:53 overwrite; the file is clean now. The writer was not proven (WAVE-FLOW-R2: coord-commit merge/restore is the suspect), so CAS in two tools may not cover it. |
| ot-job / ot_store relink, 48 h age-out | TOOK. Free scratch 13:45 -> 14:40: intel1 254 -> 1148, epyc8 1368 -> 2187, epyc9 1382 -> 2178, epyc10 912 -> 1152 GB. epyc2 not helped (66 GB). Since 14:40 the six hosts lose about 590 GB in 53 min (254 GB/h before the reap); cause not traced. |
| clock-buffer halo da13a203f90 | LANDED 15:31, NOT EXERCISED (same reason as port-hold). |

## Classes

### A. Memory overcommit and guard kill storm: 41 verdicts, 26 wave FAILs, rising
- Count: infra-oom verdicts 41 (2 / 26 / 13 by hour; none listed as a class at 1400). kills.log: epyc10 30 today (10 in the 13 hour, 20 in the 15 hour, still
  firing at 15:49), epyc8 6. Victims: col_h9_r1 15, slice_station 8, col_h9_r2 7. 7 PREGRT_HOLD_FALLBACK "rc 137", 4 EARLYOOM-RESUBMIT.
- State at 15:49: epyc10 960 of 1007 GB used, 74 openroad hold 939 GB, load 295 on 96 threads; epyc8 886 GB used, load 178. epyc7 642 GB and epyc9 381 GB
  available; epyc7 and intel1 have 21-36 idle threads.
- Root cause, three parts. (1) Admission reads free memory now ("admits 32 GB, reserve 0, fresh 0, peak 0"): a job admitted small grows later, and the
  measured-peak admission the owner approved on 11-14 is not active (peak 0 on every host). (2) S81 gen_hosts is epyc10, intel1, epyc2, epyc8, so S81
  cannot use epyc7 or epyc9 (1400 class G; the d8t tree copy to epyc7 is at 23 of 57 GB, link about 3 MB/s). (3) The guard kills by age: victims are
  1.2-1.9 GB openroad processes, so 20 kills free about 40 GB while the 74 old processes keep 939 GB. The storm does not relieve the pressure; it
  only removes the newest work, which is then resubmitted to the same host set.
- Structural fix (self-stopping, no new gate): ot-run admits on kit_peak_gb (the p90 the wave already records, 5.94 GB disk / per-type memory) as
  the job's reservation until the job's own RSS passes it; that is the admission rail working on a measured number, not a new limit. The guard
  picks the victim whose kill frees the most memory per lost CPU-hour, not the youngest. Tree replication to all 6 hosts starts at publish, so
  gen_hosts is never the reason a full host is chosen.
- Owner: FLEET-OPS-R (ot-run admission, guard victim rule), TOOLS-DECOUPLE (replicate at publish). Share: about 3% lost directly (41 killed jobs plus
  their restarts); epyc10 at 3x thread oversubscription with memory at 95% slows about 110 jobs, not counted.

### B. Deleters of routed results of unsigned kits (the near-miss loss)
Named in rt/current, with state:
1. `autopilot.py` PROBE_DELETE, called from `record_failure` (line 3217) and the DONE-* release pass (line 3345): rmtree of run/results and
   run/objects on every NEAR-MISS / STRUCTURAL verdict. FIXED cc35e3cf61 at 15:35 (both call sites share the script). Cost today: t47 a7, hd_ctl a2,
   t24 a21, t26 a25 and others.
2. `kit_wave.py` `grt_arm_reclaim` (line 10018), reached from `reclaim_at_result`, `reclaim_terminal_sweep` and `grt_arm_cancel(reclaim=True)`
   (supersede_on_switch, die switch, REAP): `find -delete` of *.odb *.def *.spef *.gds *.oas in the attempt dir. OPEN. Its only routed test is "a
   signoff.json exists". A routed attempt that is cancelled or superseded before sign-off wrote its json (in sign-off, in late ECO, waiting on
   LEC) loses 6_final.odb and .spef. 38 RESULT-RECLAIM and 6 RECLAIM-SWEEP lines in the window.
3. `fleet/auto_retire.py` `attempt_candidates` + `strip_keep_reports`, run by ot-auto-clean.timer every 30 min on 6 hosts (AC_FULL=1; epyc10
   deletes 47-50 dirs per pass). OPEN. FAIL / CANCELLED / SUPERSEDED attempts go 30 min after a newer attempt exists or the event changes; only
   rows carrying q_signoff, and the newest failed attempt of a type for 24 h, are kept. No 6_final test: a routed attempt without q_signoff in
   its row, or with no state row on an old event, is stripped to reports/ and logs/.
4. `fleet/kit_slim.py --strip`, class "old". FIXED 3e508626c00 at 15:29 (keeps 5_2_route, 5_3, 5_route, 6_* and config.mk unless a newer attempt
   routed or the attempt is SIGNED in the ledger).
5. `die_plan/stage_odb_cap.py` inside the kit: deleted 5_2_route.odb. FIXED 8f3d1679753 for kits generated after 14:02; older running kits are
   covered by the hardlink unit ecoseed-guard-1118.
6. `fleet/ot_store.py` gc, 48 h age-out (76cd9fef2dc): the store copy of an unsigned routed tree is unpinned after 48 h. By design; the kit
   copy is then the only one, so 2 and 3 decide.
7. Manual lane passes: FLEET-OPS-R 14:11 deleted six routed NOT SIGNED attempts on kw24 / kw26 (116 GB) on the rule "signoff.json says NOT SIGNED".
8. `fleet/ot-autoclean.py` class a (whole attempt dirs older than 6 h): same rule as 3, but its timer is not installed on the hosts I checked.
- A path that never returns the results: not found. The ot-job return copy runs on every exit (TOOLS-DECOUPLE trace, and the two epyc9 kits
  confirm it). Containers that still mount a finished kit 20-50 min later (4 "DELETE deferred" lines) are a leak, and today they saved two kits.
- Structural fix (makes the class impossible): one predicate in `ot_delete_guard.refuse()`, which every deleter already calls (r359): a
  directory that holds a 6_final.odb is refused unless (a) a SIGNED record for it is in the export ledger, or (b) a newer attempt of the same type
  holds a 6_final.odb. Then 2, 3, 7 and any future deleter inherit it and the per-tool tests can go. grt_arm_reclaim and auto_retire stop
  using signoff.json / q_signoff as a stand-in for "routed".
- Owner: FLEET-OPS-R (guard predicate), WAVE-FLOW-R2 (grt_arm_reclaim). Share: each lost near miss costs a full re-route (6-12 h of one job); at
  least 4 today, about 1-2% of fleet time, and the nearest sign-offs.

### C. Late ECO never runs: 4 of 4 in the window, 16 today
- All four end in "prd_mk.sh failed (pass dir not staged)". Read on epyc9 (sle_hc0 cl4baa7c9c a4, eco_20261118_223330): the ECO ran
  `admission_tools/01e4766cac5f.../die_plan/post_route_drv/prd_mk.sh`, the bundle frozen when the route job was admitted. That prd_mk has no
  6_final fallback (line 38: "lacks 5_2_route.odb", exit 2), and the kit's 5_2_route.odb was already deleted by the old cap. So 8f3d1679753
  cannot reach any route job admitted before 14:02, which is every job that finishes routing in the next 6-12 h.
- Second fault: eco_loop reports every prd_mk exit as "pass dir not staged", so "seed missing" and "staging failed" look the same.
- Structural fix: the late ECO is a repair step after the measured flow, so it takes post_route_drv from rt/current at ECO time, not from the
  admission bundle (the bundle keeps pinning sign-off and LEC). eco_loop puts prd_mk's last line into the reason. Then one ECO pass over the
  kits that still hold 6_final.odb (the two sle_hc0 kits on epyc9 now; hold FF -21.57 and -45.53, TT -29.85 and -13.52, DRC 0).
- Owner: TOOLS-DECOUPLE. Share: under 1% compute; 4 probable sign-offs per 2 h.

### D. A known structural verdict still launches: col_h9_r1 / r2 on d8t, cbx_q10
- 60 col_h9_r1 rows live on event 3fa87b84b18 (23 running), 58 col_h9_r2 (8 running), 4 cbx_q10. They are also the top memory-kill victims (22 of 41).
  The 15:22 relaunch was released by the wave itself: GRT-EDGE auto sets OT_GRT_TRANSITION_MODE after a GRT overflow, which changes the env hash.
- Root cause: the stop exists as a command a lane must run; nobody ran it, and the old hold was removed first. An automatic env edit counts as
  "a fix" for SKIP-SAME-INPUT.
- Structural fix: the classifier that writes structural.tsv writes the struct_stop entry itself for verdicts that name a plan cause (GRT-0116
  with a plan-block hash); no lane step. Env keys the wave sets on its own (GRT-EDGE auto) are excluded from the release hash, or allowed once
  per plan block. Now: COORD or S81-COL-FLOW runs `kit_wave.py cancel-rows` for col_h9_r1 on d8t.
- Owner: WAVE-PILOT-FIX (auto stop, env exclusion), S81-COL-FLOW-1118 (cancel-rows today). Share: about 5% (31 running jobs for 2 h).

### E. Tick 1,300-1,600 s: results and launches wait up to 27 min
- poll_running 885 / 220 / 468 s, orphan_sweep 600 s (its timeout), collect 128-270 s. Probe errors: "epyc8 timed out after 120 seconds",
  "epyc7 not checked: rc 1" (a Python traceback tail) on 5 CANCEL-STOP lines. The slow hosts are the overcommitted ones (class A).
- Root cause: the tick runs per-job remote probes in sequence with 120-1800 s timeouts; one loaded host stalls the whole fleet's loop.
- Structural fix: one batched probe per host per tick, hosts in parallel, with a per-host budget (60 s); a host over budget is skipped for
  that tick and its rows keep their state. orphan_sweep runs every Nth tick. Owner: WAVE-FLOW-R2. Share: 0% compute; about 15 min mean delay on
  every verdict and launch, which is why SUBMITs fell from 78 to 51 per hour.

### F. Orphans found late: 16 KV jobs with logs idle 11-13 h
- 16 infra-orphan verdicts on KV-HG6 / KV-D22 rows ("client lost, kit logs idle 11.1-13.0 h", 4 more at 3.0-3.2 h), found only when the die switched
  to KV-D23H and cancelled them. REAP-DEAD SILENT printed 156 "reported only" lines meanwhile. 16 KV types had no live build for half a day
  while counted as running.
- Structural fix: ORPHAN-DEAD (no client, container or process for 10 min) is the existing rule; apply it to rows the SILENT reaper lists
  instead of "reported only" (CPU check first, per the 11-13 lesson). Owner: WAVE-FLOW-R2. Share: 0% compute, 16 types x 11 h of schedule.

### G. A type-level fact is re-learned on every plan event: KV cell cap, 14 FAILs
- kv3_hub_C 709,137 cells, kv3_hub_Wo 401,310, kv3_pv_v2n 404,232, kv3_pv_v3n 411,146 fail OT_NATIVE_CELL_CAP at floorplan, 2-3 times each in
  65 min, each time as attempt 1 of a new KV event. The cap is the r576 limit the owner asked to delete on 11-14; three of the four are 0.3-2.8%
  over it.
- Structural fix: delete the cap check as ordered (the three near-cap types then run); the measured count is stored per RTL / partition digest
  so hub_C (above the 517 k largest closed run) is skipped by SKIP-SAME-INPUT across events until its partition changes. Owner: KV die owner,
  WAVE-PILOT-FIX. Share: under 1%.

### H. STALE and non-design rows
- STALE 105 current-event, unchanged: HBM 104 (parked; 11 unowned), QC 7 (CANCELLED SUPERSEDED 04:25, now 11.3 h, owner KIT-WAVE-1 6, DIE-QC-97 1;
  second report with no relaunch). Non-design: S81 global_place error 5, other flow error 3; QC other flow error 4 (the su_l1 kit_istations
  depth [4, 5], a real bind fact, owner DIE-QC-103), cancelled superseded 9. gunit__t1 is at attempt 15 on KIT_PREFLIGHT "issues 5".
- Log noise: CELL-BIG 2,645 of 3,861 lines (68%), TOOLS-LAG 25, REAP-DEAD SILENT 156. Unchanged since 1400.
- Post-CTS stops (8) delete run data at once ("DELETED failed run data", 10 lines): those are not routed, but the Fable lanes need the
  4_cts.odb of the newest one per type; auto_retire keeps it 24 h, PROBE_DELETE does not.

## Do now (ranked)
1. FLEET-OPS-R: measured-peak reservation in ot-run admission; guard victim by memory freed; S81 tree on epyc7 / epyc9 (class A).
2. FLEET-OPS-R + WAVE-FLOW-R2: routed-unsigned refusal inside ot_delete_guard.refuse(); covers grt_arm_reclaim and auto_retire (class B).
3. TOOLS-DECOUPLE: late ECO reads post_route_drv from rt/current; rerun the ECO on the two sle_hc0 kits on epyc9 (class C).
4. S81-COL-FLOW-1118 / COORD: cancel-rows for col_h9_r1 on d8t now; WAVE-PILOT-FIX: classifier writes the struct stop (class D).
5. TOOLS-DECOUPLE: the publish_apply bind_matches self-check is still missing.
6. WAVE-FLOW-R2: per-host batched probes with a budget (class E); SILENT rows go through ORPHAN-DEAD (class F).
7. KV owner: delete the cell cap check, split hub_C (class G).
