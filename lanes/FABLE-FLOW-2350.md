# FABLE-FLOW-2350: procedural / flow review, window 11-20 21:45 to 23:55 PST

Lane FABLE-FLOW-2350 (Fable 5.2). Read-only review, process and tooling only. Nothing cancelled, signalled or launched.
Previous: lanes/FABLE-FLOW-2200.md.
Sources: autopilot/log.txt (1,579 lines from 21:45), lanes/FLOW-HEALTH.tsv (23:07), tools/failure_breakdown.py (23:55),
`ot-run --status` (23:5x), lanes/NOPROG.tsv (23:37, 303 jobs), lane posts and handoffs, LANE-STATUS.tsv, kit_wave.json,
rt/current f453583d583, live 5_1_grt logs in the ot-jobs work dirs on 7 hosts, the FLEET-WATCH-2000 push logs on epyc7.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.

## Headline

1. **73 percent of the memory-hours held by running jobs sit in jobs that are old-plan, oversized, or 12 h+ in global route (V).**
   Old-plan wave rows alone are 49 percent. Table in class (e).
2. **The long single-thread stage is the global-route congestion loop, not repair_timing, detail placement or STA (V).**
   97 jobs are 6 h+ in it (2,113 GB, 63 percent of memory-hours). The tool is single-threaded there; more threads do not help.
3. **The watchdog still cannot see these jobs (V).** The fix is on main (f3db2d0e628) but the installed watchdog differs
   from main on all 7 hosts, and the watchdog reads the kit directory while the job writes its logs in the ot-jobs work
   directory. 137 of 303 jobs still read `stage_odb_cap`.
4. **A push that touches kit_wave.py cannot land (V).** Its test set runs 38 min; main moves 15 to 20 times an hour.
   FLEET-WATCH pushes 4 and 5 lost 1.9 h and the owner-approved launch skip is still not on main.
5. **WAIT-VISUAL holds 45 routes through a second config key (V).** `visual_gate = signoff` and `wait_visual = false`
   are set, but `review_before_route {event: current, all_items: true}` on S81, KV and QC holds every placed type.
6. Sign-off count: 474 any plan at 22:15, 492 at 23:05 (R, SIGN-RATE; the 23:05 row uses a new format, so the step is not confirmed).

## Classes

Memory-hour shares are of 48,035 GB-hours (5,177 GB, 303 jobs) in NOPROG.tsv 23:37.

### (a) Pushes rejected because main moved

- Count (V): 28 real ot-push-main runs in the window (25 harness runs of PUSH-FIX-2300 and mq1 excluded), 9 failed
  (32 percent; 2200 window 24 percent; day 27 percent). 3 ended rc=3 (rebase after a refused push), 6 rc=4 (tests).
  Of the 7 runs with tests over 300 s, 4 failed. Wall time lost on failed runs: 2.4 h, of which FLEET-WATCH-2000
  push 4 (2,303 s) and push 5 (4,627 s, the suite ran twice). Push 6 has been testing since 23:21.
- Root cause (V): ot-push-main already does fetch, rebase, retry and re-runs only affected tests (00a409587516). That
  works for short test sets. A change to tools/autopilot/kit_wave.py (17,622 lines) selects all 124 kit_wave test files,
  run serially (`pytest -q -x`, no `-n`) on a host at load 110: 38 min. Main took 20, 15 and 4 commits in hours 21, 22
  and 23; kit_wave.py itself changed 15 times since 12:00. The push is refused every time, the moved files overlap,
  the suite re-runs, and the second rebase conflicts. The conflict message prints an empty file list (tool defect).
- Structural fix (P): a single-writer merge train. ot-push-main pushes the lane's commits to `refs/train/<lane>-<n>`
  and waits. One runner on intel2 (no LLM, reserved 16 threads outside the wave count) takes every queued ref,
  rebases them in order on main, runs the union of their tests once with `-n 16`, and pushes. A lane whose commits
  fail or conflict is dropped from that train and gets DIED with the file list; the rest land. Main then moves only
  by the train, so "main moved during the test" cannot happen. First step, today: `-n 16` in the gate (38 min to about
  4) and the conflict file list.
- Owner: FLEET-WATCH-R3 (PUSH-FIX-2300 wrote the current tool). Fleet time: under 0.1 percent of machine time; the
  cost is fix latency, 2.5 h and counting for the launch skip and the guard-kill victim rule.

### (b) Lanes that stop with no armed waiter, or hand items to lanes that are gone

- Count (V): since 21:45, 51 posts were addressed to stood-down lanes that have a LANE-STATUS row (redirected), and
  38 to lanes with no row that have been silent 1.5 h or more (RESET-RELAY-GEN-R3 10, KV-PLAN-R1 4, FLOW-NOADV-R3 3,
  FLOW-NOADV-R4 2, S81-DIE-R3 2, QC-PLAN-R3 2, others). 13 more name no lane at all ("die owners", "KIT-WAVE").
  Case: FLEET-WATCH-2000 23:16 handed the admission skip to FLOW-NOADV-R4, whose last post is 20:50; no row for either.
  Six lowercase twin post files exist today (mem-reclaim-2200.md, qc-plan-r8.md, s81-j6.md, flow-noadv-r2.md,
  fable-fix-s81-leaf-r3.md, flow-noadv-0915.md): ot-run DONE/DIED posts go to the OT_LANE name as typed.
  LOOP-GAPS lists items whose owner is a lane with no file (HEAD-CROSSING-1119, 13 rows, 22 to 26 h).
- Root cause: liveness is declared by hand (a row someone must remember to write) and only post.sh reads it. OWNERS.tsv,
  kit-wave owner fields, hold texts and retry keys name lanes with no check.
- Structural fix (P): liveness is measured. A 5-min cron writes lanes/LANE-LIVE.tsv from the last post time, the ot-wait
  registry and running units by OT_LANE. One function `resolve_lane(name)` (case-folded, follows successors) is used by
  post.sh, ot-run posts, owners_sweep and kit_wave owner fields. A post or owner field that resolves to a lane with no
  activity for 90 min and no armed waiter is also delivered to COORD as NO-READER. A lane with running units and no
  armed waiter is listed as NO-WAITER in the same file.
- Owner: POST-ROUTE-2200 (or its successor). Fleet time: none measured; delay of hours per item.

### (c) Guard layers that hold work forever

- HARVEST (V, R): 73 HARVEST-0330 entries added 03:30, untouched for 20 h; 67 were redundant (type signed since),
  about 840 GB (R, HARVEST-ECO-2350). MEM-RECLAIM-2200 freed 0 GB on intel1: 9 paths refused by the list, 4 by
  routed_unsigned_refusal. The owner released the 67 at 23:32; the list went from 127 to 60 HARVEST lines at 23:47 (V).
- WAIT-VISUAL (V): 45 route holds (KV 21, S81 20, QC 4); 1 at 02:00, 64 at 15:49, 34 at 20:20, 45 now. Verdicts arrive
  (36 in hours 21 to 23; auto review accepted 31, held 7), but every new attempt waits again. Other holds: SKIP-HELD 52,
  WAIT-FORM 48, KW-FIX-45 8 (since 11-11). HBM: 104 of 112 STALE rows and 13 ADOPT-GUARD alerts (die is parked, no flag).
- Root cause: a hold is free text with no end condition a machine can test. The visual gate was moved to sign-off on
  11-13, and a second key `review_before_route` (Codex "exact review holds") was re-pointed at each new event with
  `all_items: true`, so the owner's rule is set and not in effect.
- Structural fix (P): every protect line and hold key carries a term the tools evaluate: `until=signed:<type>`,
  `until=verdict:<attempt>` or `until=<time>` (default 24 h). guard-refresh and the wave tick drop entries whose term
  is met and log each. `review_before_route` accepts an item list only (no `all_items`) and expires with the term;
  with the gate at sign-off the route starts and a BAD verdict cancels it. Decision for COORD: the 09:03 handoff said
  keep the exact review holds; the owner says visual never blocks. I recommend removing `all_items` on the 3 dies.
- Owner: FLEET-WATCH-R3 (terms), die owners via kit_wave_edit (the 3 keys). Fleet time: 0 memory; 840 GB disk; 45 types
  placed and not routing.

### (d) Retries on unfixed causes

- Count (V): cone error ("5 cone has more than 47400 cells") 6 fails on 6 serdes items in the window, same text; class
  breaker opened 22:31. Then 8 serdes retry keys were put in the S81 config and RETRY-KEY-LAUNCH relaunched 5:
  t4 is on attempt 14 (cap stop at 13), t12 on 9, t1__clfe1f0815 on 8 (cap stop at 7). FAM-S81-SERDES took them at 23:39
  (R); whether an input changed I did not check. ResetError: 0 in the window (ended 20:40). QC slw_hc3: 3 gen fails,
  then 2 place fails on 2 items (the failure moved forward, so something changed). "OOM kill, memory x1.5": 10 QC items
  (2200: 3); no guard kill is logged in the window on any host, so the kill cause is not known.
- Root cause: a retry key overrides the same-input skip, the class breaker and the cap in one step and asks for no
  evidence. Old runtime: rt/current moved 7, 7 and 5 times in hours 21 to 23 and the per-launch re-read is not in the code.
- Structural fix (P): a retry key has the form `item@N:fix=<sha or env name>`. The wave already computes the launch
  digest; a keyed launch whose digest equals the failed attempt's is refused as RETRY-SAME-INPUT and the key is removed.
  The memory x1.5 step applies only when the kill record names that container.
- Owner: FLEET-WATCH-R3; FAM-S81-SERDES for the 8 keys. Fleet time: under 0.5 percent (place-stage deaths).

### (e) Fleet time on jobs that cannot sign

| Holder (V) | Jobs | GB now | GB-hours | Share |
|---|---|---|---|---|
| Old-plan wave rows (S81 b05c, 3fa87, 465c; QC R4A4, N46C; HEAD r8b, r11b), incl. 16 ECO | 121 | 2,382 | 23,654 | 49 percent |
| Lane private builds | 71 | 1,386 | 16,542 | 34 percent |
| Current-event wave rows | 102 | 1,247 | 6,169 | 13 percent |
| In global route 12 h or more (overlaps) | 39 | 852 | 18,531 | 39 percent |
| Flagged over 400k cells (overlaps; 101 types flagged today) | 41 | 425 | 6,350 | 13 percent |
| Union: old-plan, or GRT 12 h+, or over 400k | 160 | 2,946 | 35,100 | 73 percent |

- Trend: old S81 and QC events were 44 percent at 21:45; MEM-RECLAIM-2200 freed 417 GB by 23:10 (R) and total held
  fell from 5,534 to 5,177 GB. Old-plan is not waste by rule; it is where the unsignable jobs are.
- Root cause: (1) CELL-BIG is "enqueued anyway (stops_off)"; 3 more over 400k were enqueued in the window. (2) The
  owner's rule of 23:10 (do not start an old-plan kit when the type has a current-plan row) is in a lane clone, not on
  main (class a). 10 such waiters, 240 GB, were counted at 23:16 (R). (3) No measured cannot-sign label (class f).
- Structural fix (P): the launch skip lands through the train. A job gets the label UNSIGNABLE from evidence the
  watchdog reads itself (setup below -300 ps in the post-GRT report, or two flat GRT rounds), and the exact unit is
  cancelled with the evidence line; no lane has to notice. Over 400k: launch one representative per family only.
- Owner: FLEET-WATCH-R3. Lane private builds: each lane lists what still decides something (S81-GEOM-OPUS did, R).

### (f) Long single-thread stages

- Measured (V, 7 hosts): every openroad process 5 h or older runs global_route.tcl (most) or detail_route.tcl. Of the
  jobs 5 h+ in 5_1_grt, 66 (about 1,020 stage-hours) stand in the congestion loop ("GRT-0102 Start extra iteration
  n/30"), 15 (about 140 stage-hours) in repair_timing, 5 in our own hooks. CPU 105 to 135 percent with `-threads 8`.
  One iteration takes 17 to 19 min on S81 leaf and KV hgi (13 iterations in 4 h 08), 4 min on QC cbn. A 30-iteration
  round is up to 9.5 h, and the new stop needs two flat rounds, so it fires after about 19 h on these types.
  Detail route does use threads (590 to 660 percent); 8 jobs are 6 h+ there, and 2 are flat (R, NOPROG).
  repair_timing: coll_core is flat at 221 violations for 7.8 h over 1,690 passes.
- Flow settings (P): (1) congestion iterations per round 30 to 10 for wave kits, so a round ends in 3 h and the
  two-flat-round stop fires at about 6 h. (2) A wall budget per round (OT_GRT_ROUND_WALL_S) that ends the round as
  NOCONVERGE evidence. (3) The no-progress stop that the maxwire pass already has (5_1_grt.repair_nostall.json), applied
  to repair_timing: stop when WNS and violation count have not moved over 100 passes. (4) No thread change: the loop
  is single-threaded; count a GRT job as 2 threads in the wave budget, which says "624 of 624 used" now.
- Watchdog (V): installed noprog_watchdog.py differs from main on all 7 hosts (FLOW-HEALTH 23:07), so the 22:44 fix is
  not running. It also resolves the stage from the kit path; the live logs are under
  /srv/opentallas-scratch3/claude/ot-jobs/<job>/work/run/logs. It must follow the container mount.
- Owner: FLEET-WATCH-R3 (watchdog install and log path), GPL-TD-AB or a new Sonnet lane for the three settings, each
  proven on one kit. Share: 63 percent of memory-hours are in jobs 6 h+ in this stage.

### (g) Lane hand-over loss at context limits

- Count (V): 3 lanes stood down on the context limit in the window (TAP-GRID-2130 22:40, FABLE-FIX-S81-LEAF 23:02,
  FLEET-WATCH-2000 23:16); 9 LANE-STATUS commits and 38 handoff files since 21:45; 15 of the handoffs mention a waiter.
  Loss seen: FLEET-WATCH-2000 ended with two unpushed fixes and an item handed to a silent lane, and has no status row.
  TAP-GRID push 054ac247c4 from a stale copy dropped the CORE-DIRECT block (R, restored 22:36).
- Root cause: the handoff is prose written from memory at the moment the lane has least context left. Running units,
  armed waiters and unpushed commits are facts the tools hold and the lane has to re-type.
- Structural fix (P): `ot-lane-standdown <lane> <successor>` builds the handoff from the tools: running units by
  OT_LANE, armed ot-wait entries, unpushed commits in the lane clone (sha, path), open posts addressed to the lane. It
  writes the LANE-STATUS row and re-points the units' posts to the successor. Lanes run it at a fixed budget (for
  example 70 percent of context or 3 h), not at the limit; COORD starts the successor from that file.
- Owner: POST-ROUTE-2200 successor with FLEET-WATCH-R3. Fleet time: none; one to three hours per lost item.

## The 22:00 fixes

| Fix | State now (V) |
|---|---|
| GRT stop after flat rounds; NOPROG ignores STAGE-CAP | On main (f3db2d0e628). Stop applies to new kits. Watchdog not installed on any host. |
| Cancel of restarting GRT jobs | Done by MEM-RECLAIM-2200: 417 GB freed (R). |
| rt re-read before each launch; one runtime per 15 min | Not done: 7, 7, 5 runtimes per hour. |
| cancel-rows `--event` selector | Not done (no such option in kit_wave.py). |
| One post-hook `4_cts_final.rpt` with a state line | Not done (no code found). TAP-GRID-2130 stood down. |
| `ot-job-sh`, DIED-SWALLOWED | Not done. |
| SUCCESSORS / post redirect | Done as LANE-STATUS.tsv, posts only (class b). |
| `rm` wrapper in lane profile | Not checked. |
| Push gate: reserved slot, CPU-time limit | Partly: timeout scaled by load, sparse cone widened (00a409587516). No slot, no `-n`. |
| RSZ self-stop (`grt_repair.json`) | Not found on main; RSZ-CRASH-2200 stood down to FLEET-WATCH-2000. |
| s81 tools_sha a real sha | Not done: still `j5tree`, TOOLS-LAG unmeasured (sixth review). |
| HBM parked flag | Not done: 13 alerts in the window. |
| Launch skip for superseded unstarted rows (owner 23:10) | In a lane clone, push 6 running. |

## Admission, disk, src skew, failures

- Admission (V, 23:5x): epyc2, intel1, epyc10 admit 0 GB; epyc9 152, epyc7 49, epyc8 32, intel2 24. Waiters 30 for
  838 GB (epyc10 14 / 436, epyc2 13 / 296, intel1 3 / 106), oldest 5.1 h. Launches 8, 19, 24 per hour. All 624 threads used.
  Guard kills: none logged on any host since 20:08 PST.
- Disk (V): no refusal in the window. intel1 scratch 218 GB free (94 percent), epyc8 520 (93), epyc9 563 (92),
  epyc10 705 (91), epyc2 root 90 percent. intel1 fell 244 to 218 GB in 2 h; it is the next host to refuse.
- Src skew (V): only hbm rows (277 modules, parked). s81 TOOLS-LAG unmeasured; KV and HEAD each miss one fix at times.
- Failures (V): 12 FAIL lines in the window (2200: 18): cone 6, QC relay-instance gen 3, QC cland place 2, 1 regen.
  STALE 112 current-event rows: HBM 104, QC 7 unowned (6 `__pv` types with no wave row), S81 1, KV 1.
- Hub: one HUB-SYNC-FAILED alert ("local untracked file in the way").

## Do now (ordered)

1. FLEET-WATCH-R3: install the watchdog from main on the 7 hosts and point it at the job work directory.
2. FLEET-WATCH-R3: `-n 16` in the push gate today; merge train next.
3. COORD: remove `all_items` from `review_before_route` on S81, KV, QC (or confirm the holds stay).
4. Settings lane: GRT iterations 30 to 10 and the repair_timing no-progress stop, one proof kit each.
5. FLEET-WATCH-R3: retry key needs `fix=`; same digest is refused.
6. POST-ROUTE successor: `resolve_lane` with case folding, LANE-LIVE.tsv, `ot-lane-standdown`.
7. Protect and hold terms (`until=`), evaluated hourly.

Not checked: ages of the 45 WAIT-VISUAL rows; whether the 8 serdes relaunches carry a changed input; the kill cause
behind "OOM kill x1.5"; the `rm` wrapper; the 23:05 sign-off step; per-iteration overflow (the log prints none);
stage hours for `stage_odb_cap` rows count from the end of placement, so the GRT shares are upper bounds by the CTS time.
