# FABLE-FLOW-2200: procedural / flow review, window 11-20 19:40 to 21:45 PST

Lane FABLE-FLOW-2200 (Fable 5.2). Read-only review, flow only. Nothing cancelled, signalled or launched.
Previous: lanes/FABLE-FLOW-2000.md.
Sources: autopilot/log.txt (1,821 lines from 19:40), lanes/FLOW-HEALTH.tsv (21:08), tools/failure_breakdown.py (21:43),
`ot-run --status` and free/df on the 6 build hosts (21:44), lanes/NOPROG.tsv (21:37, 334 jobs with GB and hours),
the live 5_1_grt logs on 7 hosts (21:5x, grep only), intel2 ot-run signals.log, lane posts.
Marking: **V** = I read or measured it this round. **R** = reported by COORD or the named lane, not re-measured.
**I** = inferred. **P** = proposal.

## Headline

1. **Sign-off count is flat for 5 h 57 min (V): signed any plan 474, current plan 409, same as 15:46.**
2. **Admission moved a little (V).** Launches per hour: 10 (hour 19), 76 (hour 20), 19 (hour 21 to 21:43).
   Waiters fell from 77 / 3.75 TB (19:52) to 31 / 702 GB (epyc10 17 / 320, epyc2 11 / 312, intel1 3 / 70).
   epyc8 shows 0 waiters now, not about 30; I found no post that says where they went.
   epyc7 admits 126 GB and epyc9 18 GB; the other four admit 0.
3. **The largest memory waste is a global route that restarts (V, new).** 28 running jobs are 12 h or older and
   have run the 30-iteration GRT congestion loop 3 to 9 times each; 24 of them are S81 leaf types.
   Together 636 job-hours, about 590 GB now, about 13,000 GB-hours (22 percent of all GB-hours held by running jobs).
   The watchdog calls all of them PROGRESSING because each restart writes log lines. Class 10.
4. **The watchdog cannot see 148 of 334 jobs (V, new).** Their stage reads `stage_odb_cap` and "last event 0.0 h
   ago": the STAGE-CAP keep/skip line is taken as progress. They hold 2,334 GB (42 percent); 62 of them are over 6 h
   in one stage (1,513 GB). Class 10.
5. Flow failures fell: 15 FAIL lines in hour 20, 3 in hour 21. The ResetError class stopped at 20:40.

## Classes

Fleet-time shares are of the 5,534 GB of container memory in NOPROG.tsv unless a line says otherwise.

### 1. Launches on the runtime the tick started with (item 1)

- Count, trend (V): 16 INFRA[tool_mix] ResetError fails in the window, 12 since 20:00, 10 after the 20:17 fix,
  on 11 S81 items. Last one 20:40:57; none in the 63 min after. Falling to zero.
- Root cause (R for the mechanism, V for the conditions): a wave tick resolves rt/current once and launches on it
  until it ends. Ticks ran 199 to 734 s in the window, and rt/current moved about 7 times in hour 20 and 13 in
  hour 21 (I, by directory time). The fail is also typed INFRA, so before 85307cdc9b nothing counted it.
- Structural fix (P): the launch tree records the rt sha (it already does, `<src>@<rt sha>`). `launch_safe`
  re-reads rt/current before each launch, and if it differs from the tick's sha the tick stops launching and
  the rows wait one tick. Second half, from 20:00 and still open: one runtime per 15 min unless the push
  carries a `Flow-Urgent:` trailer. A fix push then reaches launches in one tick and never mid-tick.
- Owner: FLEET-WATCH-2000. Fleet time: under 0.2 percent (each fail dies at gen or kit_rtl in minutes).

### 2. A job reports DONE rc=0 while its script failed (item 2)

- Count (V): 8 GPL-TD-AB jobs, 20:05 to 20:06, each 1,222 to 1,309 s at 12 GB. One lane, one event.
- Root cause (R, FLEET-WATCH-2000 20:49, verified there): ot-run carries the real rc; ab.sh ends in
  `echo rc=$?` and a grep, so the script exits 0. The A/B then had no result and nobody was told.
- Structural fix (P): `ot-lane-clone` writes a job wrapper `ot-job-sh` that lanes use in place of `bash x.sh`:
  it runs with `set -euo pipefail`, and ot-run posts DIED when the job log's last `rc=` or `exit` line is
  non-zero while the process rc is 0 (one line check at DONE). A swallowed rc then shows as DIED-SWALLOWED.
- Owner: FLEET-WATCH-2000. Fleet time: 8 x 12 GB x 0.35 h = 34 GB-hours, under 0.1 percent; cost is one lost
  A/B round, about 1 h of the lane, and 361 REQUEUE lines on epyc10 for that lane (V, signals.log).

### 3. cancel-rows selects by item name only (item 3)

- Count (V): 9 CANCEL-ROWS lines in the window (5 at 19:40 "no queue job", 4 at 21:01 "queue job closed").
  151 superseded-event rows are in the wave (20:00: 106). S81 has jobs running on 4 events at once (V, table below).
- Root cause: as at 20:00. Row identity for a person is the item name; the wave's own keys are (item, event).
  85307cdc9b keyed the ledger and cap by item@event (R); the cancel side is not there yet.
- Structural fix (P): the `--event` / `--attempt` selector in flight, plus: `cancel-rows` with a bare item name
  refuses when that name is live on more than one event and prints the events. No change for unique names.
- Owner: FLEET-WATCH-2000 (in flight). Fleet time: none directly; it is why old-plan attempts that are measured
  unable cannot be cancelled one by one, which feeds class 10.

### 4. Clock conclusions from the pre-hook report (item 4)

- Count (R, FABLE-CLOSURE-2130 21:21): 252 kits scanned; S81 b05c setup median -260 pre-hook, -200 post-hook;
  QC N46C -66 against +5. One stop item on J6 col volume and the root_entry_negedge rows were raised and withdrawn
  (R). root_entry_scan.py reads the post-hook report since 21:25 (R).
- Root cause: two files describe one stage and the older name sounds final. Nothing in the name or the file says
  that hooks ran after it.
- Structural fix (P): the hook step renames the raw file to `4_cts_prehook.rpt` and writes the post-hook report
  as the only `4_cts_final.rpt`, with the line `OT_CTS_REPORT hooks=<list> state=post` at the top. A reader that
  wants a clock number calls one function (`kit_reports.cts_final(kit)`) that refuses a file without that line.
  Old kits keep working: the function falls back to `4_cts_post_hook.rpt` when it exists.
- Owner: TAP-GRID-2130. Fleet time: no machine time measured; about a day of lane conclusions on S81 clocks (R),
  and at least one build decision (the J6 stop) made and reversed.

### 5. Fixes posted to lanes that had stood down (item 5)

- Count (R): 2 cases today (monitor-pin rows to S81-DIE-R4, QC cb rows to FABLE-FIX-QC-CB). I did not re-read them.
  Related (V): 13 QC types and 1 KV core are STALE with owner "unowned"; 20:00 had QC 2. The 12 new QC rows are
  `__pv` variants with no kit-wave row.
- Root cause: a post is addressed by a lane name, and a name does not say whether anyone reads it. A stand-down
  writes a handoff but does not redirect the name.
- Structural fix (P): `lanes/SUCCESSORS.tsv` (lane, state, successor), written by the stand-down step itself.
  `post.sh` reads it: a post addressed to a stood-down lane is delivered to the successor's file as well and the
  poster sees `REDIRECTED <old> -> <new>`; with no successor the post goes to COORD with `NO-READER`.
- Owner: new Sonnet lane **POST-ROUTE-2200**. Fleet time: none measured; the cost is hours of delay per fix.

### 6. rm -f by lanes (item 6)

- Count (R): 3 today. I found 2 self-reports in posts (V): OPUS-FIX-S81-BKSEL-R4 20:55 "rm -f of my own log",
  S81-DIE-R5 21:41 "ot-delete only from now on". No loss reported.
- Root cause: the rule is text. `rm` works, `ot-delete` is longer, and a lane's own log looks harmless.
- Structural fix (P): the lane shell profile that `ot-lane-clone` installs defines `rm` as a function that passes
  plain files inside the lane's own clone or job directory to `ot-delete` and refuses everything else with the
  ot-delete line to use. No new gate on builds; it only replaces the command a lane types.
- Owner: FLEET-WATCH-2000. Fleet time: 0.

### 7. Pushes that fail in the test gate (item 7)

- Count, trend (V): 37 ot-push-main runs in the window, 9 died (24 percent; 20:00 window 17 percent; today 27 of
  109). FLEET-WATCH-2000 lost 3 (666, 670 and 908 s). Its third died on **"tests timed out after 900 s"**, not on
  inputs (V, push3 log): the test host had load 150 on 96 threads. 5 others died in 4 to 43 s, which is the
  missing-input pattern (I), and 1 after 788 s.
- Root cause: two separate ones. (a) A sparse clone does not hold what the tests read, and the gate finds that
  out after minutes. (b) The gate runs on a build host at 150 percent load with a fixed 900 s limit.
- Structural fix (P): (a) ot-push-main starts with a 5 s preflight: the test inputs listed in one manifest must
  exist, else it widens the sparse set itself and continues. (b) The gate runs in a reserved slot (16 threads on
  intel2, outside the wave's thread count) and the limit counts CPU seconds of the tests, not wall time.
- Owner: FLEET-WATCH-2000. Fleet time: about 0.9 h of lane wall time in the window, machine share under 0.1 percent.
  The real cost is that every flow fix above arrives 10 to 40 min later.

### 8. Memory-bound fleet, no sign-offs (item 8)

- Count (V): 334 jobs hold 5,534 GB. All 624 wave threads are used on every tick. Per host MemAvailable 130 to
  355 GB of 1,007. Rows not launching 204: q_running 54, WAIT-FORM 49, SKIP-HELD 49, WAIT-VISUAL 38, KW-FIX-45 8.
- Root cause: memory is held by jobs that are old, not by many jobs. Jobs over 12 h are 78 of 334 but hold
  39,700 of 58,300 GB-hours (68 percent). Jobs over 6 h in one stage hold 80 percent. See the ranking below.
- Structural fix: class 10. Owner: FLEET-WATCH-2000. Fleet time: see ranking.

### 9. RSZ-0074 leaves the GRT DB unrepaired (item 9)

- Count: I found no post from RSZ-CRASH-2200 yet, so no census number here. Known cases (V, posts): S81-DIE-R5
  proof6/r2 ended with TT -377 unrepaired after the crash; a QC coll_ftc proof on 11-19 the same.
- Root cause: the repair step ends with an error, the flow keeps the pre-repair DB under the post-repair name and
  goes on, so the next stages spend hours on a DB that was never repaired.
- Structural fix (P): the repair hook writes `grt_repair.json` (state ok / crashed, error id, slack before and
  after). On `crashed` it retries once with the failing net excluded (the id is in the message), and if that
  also crashes the kit stops as FLOW[rsz_crash] with the DB named `5_1_grt_unrepaired.odb`. Detail route does
  not start from a DB with that name. That is self-stopping and frees the route memory.
- Owner: RSZ-CRASH-2200. Fleet time: not measured; each case costs the whole route stage, 20 to 26 GB for 10 h or more.

### 10. New: GRT that restarts, and a watchdog that cannot see it

- Count (V): 114 live 5_1_grt logs. 31 have run the "extra iterations" loop 3 or more times, 15 five or more,
  top 9 rounds (S81 leaf t7 and t33 on epyc8, 34 h, 132 to 136 iterations). 28 are 12 h or older.
  43 logs end on "GRT-0273 Disabled NDR for net clknet...", so the clock rule was dropped to reduce congestion.
  By type: S81 leaf 24, QC sle_ctl 3, KV 3, QC slw_su_l1 1.
- Detail route, same pattern (V, NOPROG): 5 jobs over 12 h in 5_2_route hold 132 GB and 5,164 GB-hours.
  col_h10_r2 pv4c1f67ff: 20 violations, no gain for 9.7 h, job 31.8 h, "advisory, no cancel".
- Root cause: (a) the resume hook (grt_stall_resume / grt183) re-enters GRT without a round limit; (b) NOPROG
  reads "a log line appeared" as progress, and the STAGE-CAP line appears every few minutes in 148 jobs;
  (c) the 20:00 proposal to turn a flat GRT label into UNSIGNABLE has no post or code I could find.
- Structural fix (P), no new gate, it is the owner's "flat repair" case:
  - The resume hook stops at the end of the second full round with `GRT-NOCONVERGE rounds=2` and the overflow
    value. The row goes to the die owner as PLAN. A leaf type that needs 9 rounds is a floorplan item.
  - NOPROG ignores STAGE-CAP lines when it picks the stage and the last event, and counts GRT rounds and
    detail-route violations as the progress measure. Two reads 30 min apart with no gain on a job over 3 h give
    UNSIGNABLE with the evidence line, and the exact unit is cancelled as it is today for setup below -300 ps.
- Owner: FLEET-WATCH-2000 for the watchdog; S81-DIE-R5 for the 24 leaf rows (which of them it still wants).

## Ranking: memory-hours on the memory-bound fleet

GB-hours are GB now times job age (V from NOPROG.tsv; I where marked). Total 58,300 GB-hours, 5,534 GB.

| Rank | Holder | Jobs | GB now | GB-hours | Share of GB-hours |
|---|---|---|---|---|---|
| 1 | GRT restarting 3+ rounds, job 12 h+ | 28 | about 590 (I, 21 GB each) | about 13,000 (I) | 22 percent |
| 2 | Lane private builds, all lanes | 72 | 1,394 | 19,037 | 33 percent, of which s81-geom-opus-d8g 30 jobs, 632 GB, 7,750 |
| 3 | Detail route over 12 h in stage | 5 | 132 | 5,164 | 9 percent |
| 4 | Old S81 events 3fa87, b05c, 465c (overlaps rank 1) | 63 | 1,332 | 18,689 | 32 percent |
| 5 | Old QC event N46C | 24 | 715 | 7,122 | 12 percent |
| 6 | Retries, stale rt, swallowed rc, push gate | - | - | under 600 | under 1 percent |

Ranks 4 and 5 are not waste by themselves: old-plan kits that can still sign stay. They show where to look.
intel2, the hub, carries 32 of these jobs and 725 GB.

What frees the most admission, in order:
1. Stop the 28 restarting GRT jobs after evidence (class 10): about 590 GB, which is 6 of the 96 GB route kits
   or about 28 leaf routes. 17 of the 31 sit on epyc10 and epyc8; epyc10 has the longest queue.
2. S81-GEOM-OPUS lists which of its 30 d8g jobs (632 GB) still decide something. Half would be 300 GB.
3. The 3 long detail routes of col_h10_r2 (78 GB, 31 to 45 h): one is flat for 9.7 h; cancel only those
   measured flat on two reads.
4. RSZ self-stop (class 9): frees one route stage per crash from then on.
Items 1 to 3 together are about 1,000 GB, 18 percent of what is held, with no row lost that could sign.

## The 20:00 fixes

| Fix | State now |
|---|---|
| Total cap per item@event, INFRA tool_mix x2 stops, cancel is final (85307cdc9b) | Works (V): BLOCKED-CAP on serdes__t1__clfe1f0815 (7) and serdes__t12 (8); ResetError loop ended 20:40. t28 was launched again at 21:39 as attempt 10; watch its result. |
| REPEAT-STOP "OOM kill, memory x1.5" | Still printed 3 times (V); not checked whether real OOM. |
| GRT label becomes UNSIGNABLE | Not done (V): NOPROG still "advisory, no cancel". Class 10. |
| One runtime per 15 min | Not done (V): 13 runtimes in hour 21. Class 1. |
| s81 tools_sha a real sha | Not done (V): still `j5tree`, TOOLS-LAG s81 unmeasured; fifth review. KV and HEAD pin manifests still missing on the hub. |
| HBM parked flag | Not done (V): 16 ADOPT-GUARD alerts in the window, 104 of 117 STALE rows. |

## Disk, admission, src skew

- Disk (V): no refusal in the window. Free: intel1 scratch 244 GB (94 percent used), epyc8 533 (93), epyc9 623
  (92), epyc10 675 (91), epyc2 root 90 percent with 207 GB. intel1 fell from 272 to 244 GB in 2 h.
- Admission (V): refusals are memory only. signals.log has 361 REQUEUE lines for one 12 GB lane job set on epyc10.
- Src skew (V): s81 489 of 18,020 modules differ from pin 3c913dbdfb23 (warn, launching). QC SRC-INCOMPLETE at
  20:12 on epyc7, epyc8, intel1 (postbind bind_cells.sv missing), 5 lines, then none.
- Hub (V): ALERT HUB-SYNC-FAILED at 21:42, "non-log local edits in the hub checkout: lanes/posts/S81-DIE-R5.md".
  A posts file was edited in place instead of through post.sh. Owner: S81-DIE-R5.

## Do now (ordered)

1. FLEET-WATCH-2000: NOPROG ignores STAGE-CAP lines and counts GRT rounds; post the 28-job list with rounds and
   hours as evidence; cancel on the flat-repair rule after S81-DIE-R5 marks the rows it wants kept.
2. S81-DIE-R5: the 24 leaf rows with 3 to 9 GRT rounds are a plan item (congestion with clock NDR dropped).
3. FLEET-WATCH-2000: push gate in a reserved slot with a CPU-time limit; rt re-read before each launch.
4. TAP-GRID-2130: one `4_cts_final.rpt`, post-hook, with the state line.
5. RSZ-CRASH-2200: `grt_repair.json` and the unrepaired DB name.
6. POST-ROUTE-2200 (new, Sonnet): SUCCESSORS.tsv and the post.sh redirect; the 13 unowned QC `__pv` rows.

Not checked: where the epyc8 waiters went; overflow values of the restarting GRT jobs (the log prints none
between rounds); GB per job for the 28 (taken as the 21 GB mean of long GRT rows); whether QC event R4A4 (57 jobs,
745 GB) is superseded by R6V1; the two stood-down posts; the RSZ census; real OOM behind REPEAT-STOP; git history.
