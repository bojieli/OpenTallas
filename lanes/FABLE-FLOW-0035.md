# FABLE-FLOW-0035: flow and procedural review, 21:43 to 23:50 PST 11-19 (read-only)

Sources: autopilot/log.txt (6,344 lines, 9 ticks), kit_wave_state.json (23:33), FLOW-HEALTH.tsv (23:18),
failure_breakdown.py (23:48), ot-run --status (23:44, 23:50), merge-queue/log, rt/history.log, origin/main log,
/etc/ot-heavy.conf and /var/tmp/ot-oom-age/kills.log on the hosts, ps of stage_odb_cap watchers on 6 hosts,
posts of FLOW-FIX-2045, SNAP-RO-1119, FLEET-OPS-R, WAVE-PILOT-FIX, DISK-INTEL1-2300, S81-GEOM-OPUS,
KV-D23-COMPOSE, FABLE-FIX-S81-LEPE. Fleet: 736 threads x 2.0 h = about 1,470 thread-hours.

Not checked: the die clock plan-root fix beyond "is in rt" (no failure line of that class in the window, no
run seen that exercises it); duplicate kits across lanes beyond the one LEPE case; whether the D8i builds on
epyc8 pass through the ot-heavy admission gate; route logs of kits generated after 22:47 (none has a route
log yet).

## Numbers
- Count: signed any plan 473, current plan 408. Unchanged since 19:44 (4 h).
- LAUNCH 111: 21:43-22:00 4, 22h 99, 23h 8 (S81 5, KV 3, QC 0, HEAD 0). QC 66 of the 22h launches.
- KIT-WAVE FAIL 107 (132 in the prior window): 64 QC SRC_MANIFEST, 27 INFRA_KILLED (OOM guard, all epyc2),
  7 KV qkd_pv_fin_s8_pin gen (attempt 25), 2 HEAD stale cohort (22:07, before the fix), 1 KV "no partition
  type" (21:45, old attempt), 6 place errors (design owners).
- Disk and admission refusals in the log: 0. FAIL_STAGE_ODB_MISSING: 0. SELF-STOP 0. SRC-BREAKER OPEN 2.
- Tick: 490-573 s until 22:58, then 849 s and 1,241 s (kit_wave_step 678 s and 1,012 s; plan_dies 300-310 s).
- ot-run 23:50: admits 0 GB on epyc2, intel1, epyc8, epyc10; epyc9 6, epyc7 39. Waiters: epyc2 35 asking
  2,256 GB, epyc10 5 asking 404 GB. Threads asked 5,945 on 736 (8.1x; 6.9x at 21:46).
- Scratch free: intel1 231 GB (94% used; 214 at 23:14, growth stopped), epyc8 588 GB (793 at 22:50, 665 at
  23:05: still falling about 95 GB/h), epyc9 1,034 (1,111 at 23:05), epyc10 590, epyc2 433, epyc7 2,060.
- failure_breakdown: STALE 104, all HBM (parked), unchanged. Non-design: QC "other flow error" 40 (the false
  src_manifest rows), QC cancelled (superseded) 10, HEAD 8, HBM 90 + 12.
- Skew: TOOL-SKEW WARN qc 416 modules, TOOLS-LAG qc 1,567 commits, hbm 2,664. epyc10 rt is one revision behind.

## Fixes of the last 2 h: live or not, and did the class stop

| Fix | In rt | Class stopped? |
|---|---|---|
| Stage-ODB placeholder + "eco" word match (f52e49e9d69, 860621e5549) | yes | PARTLY. Every watcher that was running at 23:21 was replaced (intel1 105 of 105 restarted, last "eco/resume process active" skip line 23:20:30; placeholder lines intel1 160, epyc8 311, epyc9 9). intel1 stopped falling. But kits whose watcher STARTED after 23:21 run the old script again: 41 of about 390 live watchers (epyc8 28, epyc9 7, epyc10 5, epyc7 1), all with the substring pattern, so they skip every pass. 20 are wave kits (kw43-wave-1109n S81 and QC), 8 are D8i private kits, 4 KV private kits. epyc8 still loses about 95 GB/h. See class 3. |
| Snapshot-independent STAGE-CAP (77973bd52d2) | yes | NOT VERIFIED. 10 kits generated in the last 70 min on intel1 + epyc9 all carry EARLY_RULES; none has a route log yet, so "route no longer re-runs floorplan and place" is still unproven. 0 FAIL_STAGE_ODB_MISSING. |
| FLOW_REFRESH_FILES (64460b81f75) | yes | NOT VERIFIED. No log line names a refresh, and 20 wave kits started old watchers after it landed. The refresh runs only on rows a new tick launches (8 since 23:00); a queued or resumed row keeps its kit copy. |
| In-GRT repair stall / wall cap (b23c1828158) | yes, 23:31 | NOT LIVE in any running kit: 0 of 178 live kits on intel1 + epyc9 hold OT_REPAIR_CHUNK, 0 OT_REPAIR_STALL lines. The commit is KNOWN-RED on main (test_tt_setup_keep::test_tcl_measure_mode_and_no_buffer_removal_at_grt, red on a serial rerun). s81 slice_station__t41 logged a 35,594 s late ECO at 23:43. |
| `finish` runs FF GRT (bf63fa6b676) | yes | Wave: not applicable (never launches finish). D8i: 0 of 114 kits on epyc8 carry the new run_kit.sh; 25 run_kit processes there still run goal finish and will die at GRT; the lane watcher resumes each once with route. D8i at 23:47: GRT 0, signed 0, 20 stopped. |
| SRC-SYNC detached copies (400c2294f2e) | yes | YES for QC: SRC-SYNC resumed (23:04 11 lines, 23:21 8 lines; none from 21:34 to 23:04). SRC-INCOMPLETE fell from 4 to 2 lines per tick. Re-opened for KV at 23:48, see class 4. |
| SNAP-RO 35a77175a03 (.orig, one list, read-only, apply check, breaker) | yes, 22:47 | NO. 64 false fails in the window (1, 1, 15, 4 on s1; 43 at 23:02 on s2). The 43 ran the verifier of their pinned rt 77973bd52d22. The breaker opened 23:02:51 and has not closed: its own re-check returns "verifier rc None" (last check 23:28). QC has had 0 launches since 22:55 with 57 eligible rows held on a tree that verifies. Second fix 68ee718a2a1 (kit ships rt/current verifier, receipt re-check, half-open probe) reached main at 23:48 and is not in rt yet. Not fixed live at 23:50. |
| STAGE_PEAK trial epyc2 / epyc8 (FRAC 0.3, set 22:55) | config live on both | Kills fell but are not 0, and they moved. epyc2: about 40 kills 21:50-22:55, 3 to 8 after, 0 since 23:20. epyc8: about 20 before, 3 to 12 after, 0 since 23:11. Admits since the trial: epyc8 20 new containers, epyc2 1 (35 waiters asking 2,256 GB stay pinned there). Untrialed hosts now kill: epyc9 4 (22:4x-23:23), epyc10 2 (23:36), intel1 2 (23:2x-23:36). See class 2. |
| HEAD wave_prepare re-digest (16e317f359) | yes | YES. 2 "prepared cohort stale" fails at 22:07, 0 after; hd_serdes relaunched 22:22. |
| Die clock tool plan-root (4ba88d2284) | yes | In rt; not exercised in the window, no verdict. |
| Host pick by load (de25a4bcef8) | yes | Not shown: 46 of 50 launches of the 22:47 tick went to epyc9 (tree presence), 8 launches since. Waiter re-pick: not landed (epyc2 35 waiters). |

## Classes, ranked by loss

### 1. QC frozen by a false src_manifest failure and a breaker that cannot close. 64 fails; open.
- Trend: 56 (prior window) -> 64. Third cause in a row for the same check (rename, .orig listing, now the
  pinned verifier). 43 NEEDS-LANE posts went out at 23:03 for one false cause.
- Root cause: (a) a kit runs the verifier from its pinned rt tree, so a verifier fix reaches only kits
  queued after the rt switch; 43 rows were queued 22:45-22:55 on the old rt. (b) the breaker re-check treats
  "verifier did not finish" (rc None) as a failure, so a slow check on a loaded hub holds a healthy die.
- Structural fix: the checker of a shared input is always rt/current (68ee718a2a1 does this). A breaker closes
  on a success receipt from any gen host; a re-check that times out is "unknown" and lets one probe row
  through. A die-level cause posts one NEEDS-LANE for the die, never one per row.
- Owner: SNAP-RO-1119 (land 68ee718a2a1 in rt, confirm the breaker drops, clear the 40 FAIL rows).
  WAVE-PILOT-FIX: one post per die-level cause.
- Share: machine under 1% (64 pre-place fails). Schedule: QC 57 rows idle for 55 min and counting; QC rows
  made no launch progress in 3 of the last 4 hours.

### 2. OOM-guard kills: 27 wave rows on epyc2, about 85 kills on all hosts. Falling, not stopped.
- Kills per host in the window: epyc2 46, epyc8 about 24, epyc9 4, epyc10 2, intel1 2, epyc7 0.
- Root cause: the gate admitted on current free memory with no growth term (11-14 setting), plan jobs
  bypass admission (adj -1000), and the guard then kills small young builds one per 10 s ("MemAvailable < 5
  percent with a plan job running"). RETRY-HOST then sent 2 killed rows back to epyc2 as "most free memory".
- Verdict on the owner rule (extend if kills about 0 and admits continue): epyc8 meets it (0 kills for 40
  min, 20 admits). epyc2 meets the kill half only: 1 admit in 55 min. Extend STAGE_PEAK 0.3 to epyc9,
  epyc10, intel1 and epyc7 now, since the kills have moved there. Keep 0.3 on epyc2; do not raise to 0.5.
- Structural fix: (a) a plan job's expected peak is charged in the admission view before it starts (it
  still starts at once, the rule is unchanged; later kits wait instead of being killed). (b) A waiter leaves
  a host that admitted nothing for 2 polls (FLEET-OPS-R soft pin 82c67b11f1a covers only new clients; the 35
  epyc2 waiters predate it: restart those clients once). (c) RETRY-HOST after a guard kill excludes the host
  with waiters.
- Owner: FLEET-OPS-R. Share: estimated 5 to 10% of fleet time (85 killed builds x 0.5-1 h x 8 declared
  threads on a fleet over-asked 8x); estimate, not measured.

### 3. A fix to a flow file does not reach kits that already exist. 41 old watchers after the fix; open.
- Same root cause in four fixes of this window: stage_odb_cap.py (41 old watchers started after the
  replace), run_kit.sh (114 D8i kits), tt_setup_repair.tcl / hold_cap.tcl (0 of 178 kits), src_manifest
  verifier (43 rows). A kit copies its flow files at gen time, pinned snapshots predate the fix, private
  lane kits are never refreshed, and the wave refresh runs only at a new launch.
- Structural fix: the kit runner resolves the flow files in FLOW_REFRESH_FILES from rt/current at every
  stage start (start of place, CTS, GRT, route, and at watcher start), by content hash, with one line
  "FLOW-REFRESH file old new". Then a fix is live at the next stage of every kit, wave or private, and the
  one-off --replace-watchers pass is not needed. Until then: cron --replace-watchers every 15 min per host
  (it is idempotent).
- Owner: FLOW-FIX-2045. Share: disk, not CPU (epyc8 -95 GB/h, floor in about 5.5 h); the route re-run of
  floorplan and place (223 of 223 routes on 11-19) stays unproven-fixed until one new kit reaches route.

### 4. Bind adoption switches kit inputs before they exist on every gen host. 3rd occurrence; open.
- 21:19 KV D25e (15 fails, prior window; cause now known: the lane deleted bindcopy_kv_d25e at apply as a
  shared-inode fix). 22:47 QC postbind tree only on epyc9 (46 of 50 launches on one host). 23:38 KV
  ADOPT-BIND repointed bind_out; at 23:48 SRC-INCOMPLETE on epyc10, epyc2, epyc7, epyc9, intel1 for the
  d25e_postbind tree (only epyc8 holds it, and epyc8 admits 0).
- Root cause: SNAP-RO apply check (c) guards apply_marker, not the post-apply ADOPT-BIND path; a lane can
  delete a bindcopy that an applied event reads by absolute path.
- Structural fix: ADOPT-BIND calls the same all-gen-host check as apply and refuses the repoint until the
  tree is whole on every host (it starts the detached copy itself). An applied event's bindcopy and
  postbind dirs are registered as live inputs in the delete guard at apply, so rm fails at the lane.
- Owner: SNAP-RO-1119 (check), WAVE-PILOT-FIX (ADOPT-BIND), FLEET-OPS-R (delete guard entry).
- Share: under 1% machine; KV relaunches wait for the copy (10-30 min).

### 5. rt sync races itself: 3 failed syncs in 45 min (22:59, 23:24, 23:40). New.
- merge-queue log 23:39: two installs of the same revision overlap ("mv: cannot overwrite ... Directory not
  empty", "chmod: cannot access .partial/*", rsync mkstemp "Permission denied" on epyc10). Each recovered in
  3-4 min so far; epyc10 is still on b23c18281582 at 23:50.
- Root cause: main lands every 3-8 min, a sync takes 1-2 min per host plus a prune, and a second sync starts
  on the same <rev>.partial dir with no per-host lock; the read-only step of one run breaks the other.
- Structural fix: one flock per host and revision around rsync + install; a revision dir that exists and
  verifies is "ok", never an error; a sync in flight coalesces newer revisions (always sync the newest only).
- Owner: OT-TOOLS-SYNC / MERGE-QUEUE. Share: 0% machine; each failure delays every fix above by one tick.

### 6. Private kits outside the wave. D8i 114 kits (55 on epyc8 without a client), LEPE dir reuse.
- D8i: launched with goal finish, 4 h in: 40 of 114 at CTS on epyc8, GRT 0, signed 0, 20 stopped; 0 ot-run
  process names them on epyc8 while 28 of their containers run, on the host with the most kills. They carry
  the old run_kit.sh and old watcher.
- LEPE: a Fable session reused the dir name proof6 and its rsync overlaid the successor's generation dir;
  one duplicate kit queued and cancelled. Nothing deleted, r2 intact, source of r2 no longer rebuildable.
- Root cause: a private kit has no registry row: no owner check on the dir, no client to adopt after a
  session ends, no flow refresh, no wave dedup against the same type and plan block.
- Structural fix: private kits launch only through one helper (ot-run --private LANE): it creates the dir
  with O_EXCL under <lane>/<session id>/ (a second writer fails), writes an owner file, and adds a row to a
  PRIVATE-KITS table the wave reads for dedup and orphan adoption (a kit whose client is gone gets a
  detached client or is stopped, never left running unlisted).
- Owner: FLEET-OPS-R (helper), S81-GEOM-OPUS (D8i now). Share: D8i about 114 x 8 threads declared for 4 h
  with 0 GRT; most of that is real build time, the loss is the GRT death and one resume each.

### 7. Retries on unfixed causes and tick time.
- qkd_pv_fin_s8_pin is at attempt 25: 7 gen fails in 2 h on a cause its owner posted (plan rows come with
  D25e2/3, not applied). BLOCKED-PLAN fires after 3, then an unblock or event relabel re-arms it. Fix: a
  PLAN-class block is released only by a changed plan block sha. Owner WAVE-PILOT-FIX. Share: 0% (seconds).
- kv3_hroot attempt_5 resubmitted "after infra-oom" at --mem 72 on intel1 (admits 0, 2 guard kills there).
- Tick 1,241 s at 23:38. With 20-min ticks a landed fix takes up to 40 min to show. plan_dies alone is 300 s
  every tick for plans that did not change: cache by plan sha. Owner WAVE-PILOT-FIX.
- hbm ADOPT-GUARD PLAN_MISSING: 20 alert lines for a parked die (unchanged since 1949).

## Share of fleet time, summary
- OOM-guard kills: estimated 5-10%. All other procedural failures: under 2% (pre-place).
- Schedule loss is larger than machine loss: QC idle since 22:55; 8 launches fleet-wide in the last hour
  while 4 of 6 hosts admit 0 GB; count flat for 4 h.
- Still the largest unknown: whether route still re-runs floorplan and place. Check the first kit generated
  after 22:47 that reaches route (run_route.log without "Running floorplan.tcl").
