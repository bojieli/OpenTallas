# FABLE-FLOW-0350: procedural / flow review, window 11-22 02:35 to 03:50 PST

Lane FABLE-FLOW (Fable 5.2). Read-only review of process and tooling. Nothing cancelled, signalled, launched, deleted or
edited except this file, one RESULT line and two posts. Previous: lanes/FABLE-FLOW-0230.md (00:26 to 02:35).
Sources: autopilot/log.txt (lines from 01:45, detail from 02:30), lanes/FLOW-HEALTH.tsv (03:08), `failure_breakdown.py`
(03:44), `ot-run --status` (03:45), ~/.local/state/ot-run/signals.log on the hub, lanes/posts/*.md (251 posts from 02:35,
50 DIED), 4 private-spec stage log dirs, `ps` on all 7 hosts (03:46) for rt versions and run-item drivers,
autopilot/kit_wave.json, autopilot/structural.tsv, rt/current kit_wave.py lines 18432 to 18455.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Not done: no bind log was opened on a build host (bind causes are from the DIED cause field and lane posts); the signals
logs of the 6 other hosts were not read (refusal counts are hub + DIED posts); the superseded-plan check is the event key
in the LAUNCH line only; wall time of the 4 relaunched kits is an estimate. "Share" = estimate (I) of fleet thread-hours
in the window (about 1,500 committed threads x 1.25 h = about 1,900 thread-hours) unless marked.

## Headline

1. **NEW, live now: one bad byte in lanes/COORD-REVIEW-QUEUE.md has switched off three autopilot steps since 02:55** (V).
   Byte 0x94 at offset 13663032, line 23842, the 02:52 RULING line ("RULING <0x94> COORD RULING, private kits count").
   Source: lanes/posts/COORD.md line 1310; tools/queue_view.py copies it into the view (surrogateescape), so the fix
   must be made in the post file or the view is regenerated with the byte.
   Every tick since logs `hold recompile skipped`, `repeat-stop tick setup skipped` and `LOOP-GAPS (aux) failed`
   (UnicodeDecodeError; 17 lines by 03:43, still failing 03:47). Effect in the code (V, kit_wave.py 18432 to 18455):
   hold auto-release, HOLD-ORPHAN release and `apply_tree_switches` (tree-ready die src switch) do not run, and
   `_unblocks = []`, so UNBLOCK lines in the review queue are not honoured. The S81 J7 apply (274 type rows held, timer
   04:14, R) depends on these steps. Posted URGENT 03:44. Not fixed by me (read-only). See class S1.
2. **Fleet 61 to 70 % busy, 184 to 187 rows not launching** (V): idle 217 to 241 of 624 cores. SKIP-HELD rose 75 to 90
   in the window. 5 wave launches in 75 min (9 in the 02 h hour, 11 in 01 h).
3. **4 of the 5 wave launches are an unchanged relaunch minutes after a STRUCTURAL verdict** (V): cbf_q00_s2 (4 min after
   -380.8 ps on the known cb path), kv3_pc_v3 x4 replicas (12 min after -1044.8 ps, same plan sha), slice_station__t37
   (4 min), serdes__t12 attempt 7 (cts.tcl error, released by `inputs:tools`, no fix commit for it on main). Class R1.
4. **The R1 family hold landed and works** (V): cb rows are SKIP-HELD with owner FAM-QC-CB-R4 and a release term from
   02:40:59; 2 more cb verdicts at -380 ps reached the log before it (02:32, 02:40), 0 after. Was 19 of 29 verdicts.
5. **Two QC binds died at 3.3 h and 2.6 h on one coll_core tap name** (V/R: QC-PLAN-R13 11,877 s, FAM-QC-SLWSLE-R1
   9,455 s; "density added tap names must be clk_t126"). TAPNAME in plan_gate_pre finds this class in seconds (R: QC-SLE-R5
   8 -> 0); both binds started before the check existed (00:05, 01:02). Class B1/T1.
6. **Hub disk hit the floor 02:57 to 03:00: 8 refusals** (V), now 612 GB free (V 03:46). Class A1.
7. **53 private run-item drivers on the hub, 6 under a supervised unit** (V, ps 03:46). Class P1.
8. **Count: signed any plan 549 / current plan 439** (V 03:44); was 548 / 438 at 02:31. 1 SIGNED verdict in the window.

## What FABLE-FLOW-0230 asked for: state now

| 0230 item | State at 03:50 |
|---|---|
| R1 family cause hold | LANDED for the cb family (V, hold with owner + term). `plan_input` for PLAN verdicts: NOT effective (V): serdes__t12 and coll_core were released by `inputs:tools` at 03:11 and 03:04; coll_core was then caught by CAUSE-CAP |
| R1 ledger | NOT landed (V): serdes__t14 "3 earlier attempt(s) not in the ledger", 6 failed attempts, attempt 7 launched on a retry key |
| U1 SKIP-HELD by key, owner, age | LANDED (V, main b6e130c60f): `UNDER-USE HELD` line prints key, owner, age, flags. It shows 59 flagged keys |
| B1 EMIT pre-checks | LANDED (R, FLOW-OPS-R2 main 4396e129eff). Not yet seen stopping a bind in this window |
| T1 `min_rt` | LANDED (V): kit_wave.json min_rt 6d2e187f0d65, rt_floor.py, private-spec refuses without `--rt-floor-exempt WHY` (R, FLOW-FLEET-R1 02:57). Bind via `ot-run --plan-job bind` is not covered (V: no min_rt in ot-run) |
| A1 hub out of the host set under 300 GB | NOT landed (V): the floor was hit 25 min later. Cleanup fixed instead (R, CLEAN-AGGR-R3: 3 guard false-blocks) |
| D1 death classes | PARTLY (V): NOT-RUN, NO-PATTERN, BIND-FAIL landed (5a9ab12224). 20 of 50 DIED still carry no usable class |
| N1 parked HBM alerts, ITEM-SYNC, NO-ROW-SOURCE | NOT fixed (V): ADOPT-GUARD hbm 24 lines in the window; ITEM-SYNC phy_serdes_b 52 today; NO-ROW-SOURCE QC 26 + S81 14 every tick |
| TOOLS-LAG false positive | Fix on main 2959d7f51b9 and in rt/current (V), but the 03:43:40 tick still prints "s81 / qwen_compute missing r708" (V). Check the next tick |
| ENV-OVERRIDE consumption check | LANDED with false-positive fix (R, FLOW-OPS-R2 03:23); not measured here |

## Classes, ranked by fleet hours

### U1. Rows that cannot launch while 30 to 39 % of cores idle. Largest.
- Count (V): idle 217 to 241 of 624 cores (was 252 to 275); rows not launching 184 to 187 (was 187 to 194). SKIP-HELD
  75 -> 76 -> 82 -> 84 -> 90, WAIT-FORM 42, q_running 39 to 43, q_fail 8 to 10, KW-FIX-45 8. Trend: flat.
  Load uneven: epyc9 113 to 140/96 while epyc2 50 to 70/128 and intel1 51 to 57/112.
- Root cause: holds without a release term. HOLD-TERM (V): s81 344 holds, 343 without owner/eta; QC 19, 17 without; KV 14,
  12 without. UNDER-USE HELD flags 59 keys, e.g. s81 col_h9_r2 36.7 h, gunit__t1 33 h, WAIT-FORM hbm 237 h (parked die)
  and s81 38.5 h, all "NO-OWNER" or "NO-ETA>24h". The report exists; nothing acts on a flag.
- Structural fix (P): a hold key flagged NO-OWNER+NO-ETA for 24 h becomes one OWNERS row assigned to the die owner
  lane, and its rows are listed in the die owner's hourly ask; HOLD-ORPHAN release (already coded) then applies. Parked
  dies are left out of the count. Needs S1 fixed first: that code path is the one now skipped.
- Owner: FLOW-OPS-R2 (rule), die owners (terms). Share: 30 to 39 % of cores idle; not all recoverable.

### S1. A single shared text file is a hard input of the scheduler tick. NEW.
- Count (V): 1 fault, 55 min and running, 3 steps off per tick (17 log lines).
- Root cause: `AP.read_coord("lanes/COORD-REVIEW-QUEUE.md")` decodes a 13.8 MB hand-appended file strictly; the three
  callers catch the exception and skip the whole step. post.sh / coord-commit accept any bytes. The file also grows
  without bound (24,075 lines) and is parsed every tick.
- Structural fix (P): (1) read_coord opens with errors="replace" (one line); (2) post.sh and coord-commit.sh refuse a
  line that is not valid UTF-8; (3) a step that is skipped for 2 ticks in a row raises one ALERT with the file and
  offset instead of a log line per tick. Immediate: replace the byte with "-" in lanes/posts/COORD.md via coord-commit.
- Owner: FLOW-OPS-R2 (reader + alert), COORD (the byte). Share: 0 measured; at risk: the 04:14 S81 J7 tree switch
  (274 rows), every hold auto-release and every UNBLOCK since 02:55.

### R1. Unchanged relaunch after a STRUCTURAL / PLAN verdict.
- Count (V): 7 verdicts in the window: 5 STRUCTURAL (cbf_q00_s2 -380.8, cbn_q01 -380.9, kv3_pc_v3 -1044.8, coll_core
  -558.3, serdes__t14 and slice_station__t37 post-CTS triage), 1 CRASH, 1 SIGNED. Was 29 verdicts, 19 one stop: down.
  Relaunches with the same plan sha: 4 of 5 launches (headline 3). GRT-ARM cancelled 2 QC units at 4.7 and 4.8 h (good).
- Root cause (V): the repeat stop needs 3 identical fingerprints, so attempts 2 and 3 of a verdict that says "routing
  cannot close it; plan fix, no unchanged retry" are free; a tools hash change releases a BLOCKED-REPEAT (main took
  23 commits in the window); the ledger still misses old attempts.
- Structural fix (P): a verdict of class STRUCTURAL / PLAN blocks the pair (item, plan block sha) at the first failure.
  Only a changed plan block or a retry key `item@N:fix=<sha>` releases it; `inputs:tools` never does.
- Owner: FLOW-OPS-R2. Share: about 2 to 3 % (I: 4 relaunches + 3 extra replicas, 8 threads, about 1 h each).

### B1. Die binds that fail late.
- Count (V): 20 bind units ended: 11 DONE, 9 DIED; 32 thread-hours in dead binds (was 28 / 18 / 99). Late: the two QC
  binds of headline 5 (5.9 h wall together), QC-SLE-R5 1,202 s (ASB_MERGE), FAM-KV-IOPC-R4 2,168 + 2,190 + 513 s
  ("RC_ELAB 0", third round of this label). Refused in seconds: 1 (disk floor).
- Root cause: a bind started before a pre-check landed keeps running without it; plan_gate_pre runs once at launch.
  The base plan error (coll_core tap name) was inherited by a second lane's bind built on the same base.
- Structural fix (P): when a new pre-check lands on main, the tick runs plan_gate_pre of rt/current against the plan of
  every live bind unit (seconds each) and posts BIND-DOOMED <unit> <rule> to the owning lane. A plan that fails
  plan_gate_pre is marked so no other lane composes on it.
- Owner: FLOW-OPS-R2. Share: about 2 % of threads; 3.3 h of calendar on the QC V3 base, which gates the QC cut.

### T1. Runtime and tree skew.
- Count (V, ps 03:46): 49 rt versions live; below the floor 30 versions / 64 processes, at or above 19 / 128 (33 %
  below; was 63 %). Started in the last 75 min on a below-floor rt: 7 versions (opus-fix-s81-colrom-r6, fam-s81-col-
  h9r0-r4, head-ctl-r1, fable-fix-qc-coll-r2, tap-grid-r5 and fam-lepe4 on the J7 pins, the last two declared exempt).
  Tree pins lag fixes (R): KV D28 tree is pinned at 6d2e187f0d65, which lacks b84fd457f5, so the pc_v3 rows move to D29
  and the binds run a fork-patched file; QC used warn-mode binds until the tap rename (R, QC-SLE-R5: strict again 03:26).
- Root cause: min_rt covers private-spec and ot-build only; the floor is one hand-set sha; a die tree pin is frozen at
  apply time and a later main fix reaches it only with the next plan event (24 h).
- Structural fix (P): `ot-run --plan-job bind` and run-item apply the same min_rt check (exempt flag logged); the floor
  moves automatically to the commit of the newest landed pre-check; a tree pin may take a cherry-picked tool fix through
  one sealed "tool-only refresh" step (manifest re-sealed, no plan change) instead of a fork-patched file.
- Owner: FLOW-OPS-R2 (check), FLOW-FLEET-R1 (ot-run). Share: about 1 %; cost is calendar (one plan event per missed fix).

### P1. Private run-item drivers outside any supervisor. NEW.
- Count (V, ps on the hub 03:46): 53 `kit_wave.py run-item` drivers of private specs: 6 under a systemd / ot-run unit,
  35 orphans with parent pid 1 (nohup or setsid from a shell), 12 with sshd in the ancestry (FAM-QC-FEFW-R3 2 since
  20:59, FAM-S81-LEPE-4, FAM-S81-SLICE-R6). 1 was found and re-parented by its lane (R, LEPE-4 03:18). The 9 wave
  drivers all run under units. Each driver is launched from whatever rt the lane used: 23 different rt shas (V).
- Root cause: private-spec prints a command line; how it is started is left to the lane. A driver that dies posts
  nothing (only its ot-run stages post DIED), and the kit stops between stages without a row anywhere.
- Structural fix (P): `kit_wave.py run-item` on a private spec re-executes itself as `systemd-run --user --unit
  pk-<lane>-<item>` from rt/current when it is not already in a unit, with OT_LANE set, so it survives the shell and
  posts DONE / DIED. One code path, no lane action.
- Owner: FLOW-FLEET-R1 (KIT-OPS for the hand-over of the 47 live ones: no restart, list them). Share: 0 measured in
  the window; at risk 47 kits, 2 to 7 h of work each.

### A1. Hub disk at the floor.
- Count (V): 8 refusals 02:57 to 03:00 at 144 to 149 GB free: TAP-GRID-R5 bind (rc 78), OPUS-FIX-S81-SVC-R9 kits
  (rc 127, PIN-FALLBACK), 6 FAM-S81-SLICE-R6 run-items (rc 78). All relaunched by 03:05 (V, ps). 0 memory refusals.
  Free: 166 GB (02:36) -> 144 (02:57) -> 248 (03:15) -> 370 (03:22) -> 612 (03:46). Other hosts 463 to 2,231 GB (V).
- Root cause (R, CLEAN-AGGR-R3): three delete-guard false-blocks made every retire pass delete 0 (exact _work roots,
  a container lease row that protected all of kw45, signed-unexported on main-tracked signoff.json), fixed 0611fc2e04,
  626ac8aca9, 8480ad8165. Still open (R): a delete RULING in the review queue names the tree, and post_trees() reads
  that as a reference, so the approval protects the tree it approves (stripbody _r2). And every private run-item is
  pinned to the hub (`--hosts localhost --dir ~/coord/autopilot/private_specs/...`), so a hub at the floor stops all
  private kit starts fleet-wide.
- Structural fix (P): DISK-RATE state 2 (floor within 2 h) starts the aggressive cleanup pass at once instead of on the
  hourly timer, and a retire pass that deletes 0 at state 2 raises an ALERT naming the top refused rows; post_trees
  skips paths named in a delete RULING / ASK.
- Owner: CLEAN-AGGR-R3. Share: under 1 % (minutes per refused unit).

### D1. Death posts that say nothing: 20 of 50 (40 %; was 28 of 85, 33 %).
- Count (V): UNCLASSIFIED 12, NO-PATTERN 6, no class 2. Of these, 9 are private-spec geom stages "rc 1, no log"
  (FAM-QC-CB-R4 x2, OPUS-FIX-S81-COLROM-R6 x2, OPUS-FIX-KV-HUB-R6 x2, FAM-S81-MISC-R4, FAM-QC-FEFW-R3, HEAD-LEP0N-R8).
  They are not deaths (V, 2 dirs read): geom.log beside geom.live.log holds `AP_AUTO_GEOM AUTO-GEOM FAIL ...`, the
  advisory geometry verdict, and the chain goes on to route. This is 0230 class K-a, still open. 3 are "RC_ELAB 0".
  The 7 disk refusals are labelled RAIL-KILL although nothing ran. The two largest dead jobs (LOCKUP-STATION proof6,
  26.7 h x 8 threads, SIGTERM "sender not mine"; FLOW-RESTORE-AUDIT rb_e8_rest 6.4 h x 16) are design proofs; the first
  was stopped by an unrecorded sender.
- Fix (P): the geom stage exits 0 when it produced a verdict line (FAIL is a verdict, not a crash) and the classifier
  reads `<stage>.log` beside `<stage>.live.log`; NOT-RUN is its own class; `--cancel` without `--reason` is refused.
- Owner: FLOW-FLEET-R1. Share: 0 direct; 9 false DIED per 75 min hide the real ones.

### M1. Pushes: 16 rc 0, 5 died (24 %; was 23 / 1).
- V/R: FLOW-OPS-R2 x3 rc 3 after about 400 s each (R: rebase conflict from its own clone edits during the run, label
  TEST-FAIL "no cause line"); fable-fix-s81-leaf-taphold rc 4 after 532 s (test_schema_file_in_sync); explorer-store-r1
  rc 4 after 5 s, no log.
- Fix (P): ot-push-main tests and pushes a detached snapshot of the commit taken at start, so later edits in the clone
  cannot conflict; the schema file is regenerated by the push tool, not asserted.
- Owner: MERGE-QUEUE. Share: under 1 %.

### N1. Ticks and checks that repeat without an actor.
- V: tick total 298 to 330 s, twice 589 and 604 s (03:05, 03:40; kit_wave_step 555 s). ADOPT-GUARD hbm 3 lines per
  tick on a parked die. ITEM-SYNC phy_serdes_b rc=2 52 times today. NO-ROW-SOURCE 40 items every tick. STALE 1: s81
  iqf__t1 ROUTE-HELD 23.5 h, owner FAIL-S81-1. RETIRE-SUPERSEDED: 1 stale ENQUEUED row, 9 superseded-event rows; no
  launch on a superseded event key seen in the 5 LAUNCH lines (V).
- Fix (P): as 0230 N1 (a line unchanged for 24 h becomes one OWNERS row; parked dies skipped). Owner FLOW-OPS-R2. Share 0.

## Requests to COORD (ranked)

1. S1 now: replace the 0x94 byte in lanes/posts/COORD.md line 1310 (and the view) before the 04:14 J7 apply; FLOW-OPS-R2 to make
   read_coord tolerant and post.sh / coord-commit refuse invalid UTF-8.
2. R1: STRUCTURAL / PLAN verdict blocks (item, plan sha) at the first failure; `inputs:tools` never releases it.
3. U1: flagged holds (59 keys) become OWNERS rows with the die owner; no hold without a term after 24 h.
4. B1 / T1: re-run plan_gate_pre of rt/current on the plans of live binds; min_rt in `ot-run --plan-job bind`.
5. P1: run-item puts itself in a unit; list the 47 unsupervised drivers per lane.
6. A1, D1, M1, N1 as above.
