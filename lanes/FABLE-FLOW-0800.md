# FABLE-FLOW-0800: procedural / flow review, window 11-22 05:55 to 07:48 PST

Lane FABLE-FLOW-0800 (Fable 5.2). Read-only review of process and tooling. Nothing cancelled, signalled, launched,
deleted or edited except this file and one RESULT line. Previous: lanes/FABLE-FLOW-0600.md (03:50 to 05:55).
This file replaces the 11-21 report of the same name (kept in the hub history).
Sources: autopilot/log.txt (1,296 lines from 05:55), journal of autopilot.service, hub ot-run signals.log (254 lines),
`ot-run --status` (07:45), `failure_breakdown.py` (07:47), RELEASE_TREE.md (07:05 count), 339 post lines from 05:55
(53 DIED, 139 DONE), rt/history.log, 3 private-spec dirs on the hub, loadavg / df on epyc2, epyc9, epyc10 (07:45).
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Not done: no git log read (shas are taken from posts and rt/history.log); no kit log opened on a build host; signals
logs of the build hosts only sampled; FLOW-HEALTH.tsv is from 07:09 and its hourly rows were not used. "Core-h" is an
estimate (I) against 752 cores x 1.9 h = about 1,400 core-hours. At-risk figures are not losses yet.

## Headline

1. **Count: signed any plan 558 / current plan 447** (V, 07:05); was 550 / 440 at 05:44. FLAT in the last hour.
   6 of the 8 are the S81 provider designs that the X1 pins backfill made countable (R, FLOW-FLEET-R2), not new sign-offs.
2. **No tick was killed** (V): 8 ticks, 405 to 804 s of the 900 s limit. The 804 s tick (07:31) carried 93 launches.
3. **Wave launches 177: S81 154, QC 19, KV 4, HEAD 0** (V). 93 of them at 07:29 to 07:31 on retry keys.
4. **18 of those 93 failed 6 min later on BIND-GEN-TOOLSKEW and the S81 class breaker opened at 07:36** (V). The hub
   rt/current moved 16 times in the window (every 7 min); two of the moves fell inside that one launch batch.
5. **The geom rc fix does not reach specs that already exist** (V): 10 geom DIED posts after the fix was on the hub rt
   (07:14). A spec resumed at 07:25 ran `geom_check.sh` sha aa290ccb (old) from its `.geom-tools-d2a73017` copy; rt
   2d4444116da2 and later hold 2e6a30a0 (new).
6. **183 REQUEUE "not admitted within 600 s", 80 RESTAGE, 57 orphan waiters reaped** (V). 133 of the requeues are
   wave kits. epyc9 alone: 77 requeues, 55 restages, 43 orphans.
7. **Fleet load is down from 1.45x to 1.17x** (V: 879 on 752 cores; epyc10 94/96, was about 190). Threads committed are
   still 417 % (3,139).
8. **epyc10 scratch2: 259 GB at 07:48** (V); 391 GB at 07:10, 270 GB at 07:39. The fall slowed to about 70 GB/h.
   DISK-RATE named no holder and AUTO-RETIRE deleted 0.

## The 0600 classes: state now

| 0600 class | State | Evidence |
|---|---|---|
| H1 no-op hold record | FIXED | R: 7d5348dba7 refuses a record on a stops-off die, removal needs `--expect-launch N`. V: HOLD-AUDIT 0 in 8 ticks, 147 S81 rows held. Part (3), audit counts ineffective records, not seen |
| W1 killed tick, double launch | FIXED | V: 0 ticks killed. R: 13 duplicate units stopped (WAVE-OPS-R1 06:01); launch journal 233947ba8aa; probe detach 43a508e4ad4 on the hub rt 07:34. Watch: tick 804 s at 07:31, before the detach |
| F1 CPU oversubscription | IMPROVING | V: LOAD_CAP 1.2 on all gen hosts (149a58c42d08); load 1.17x; reps-first shows in FAMILIES lines (S81 70 reps, 100 siblings held). Threads 417 %. Side effect: class P1 below |
| K1 plan cut loses rows | IMPROVING | R: cut ledger bc9603f67b; 3 DROPPED-ROWS posts at 05:55. V: KV recheck 05:59 "no ledger yet"; no compose has switched to it |
| G1 1 h single-core check | IMPROVING | R: 5bb9a043e39 (56 s cold) and c19dbd9b5e6 (beside bind). V: 5 plan_gate_pre units still died after 2,561 to 3,823 s (launched before the fix). New: class L1 below |
| C1 goal words | IMPROVING | R: goal table 149a58c42d08. V: DIED class SETUP 6 (was 18), no rc 10. Old drivers: class S1 below |
| E1 test starts fleet work | SAME | R: harness guard "in test", not on main. V: epyc10 signals.log 15:01 to 15:05 UTC holds test lines (hosts epyc4, agi, dir /srv/x) |
| X1 false / missing signals | IMPROVING | R: S81 designs 72/72, hub sync f4e0e522b00. V: 1 HUB-SYNC-FAILED (06:03, signed-store record + tools/signed_store_ingest.py). DIED posts still mix UTC and PST end times |
| D1 unclassified deaths | WORSE | V: NO-PATTERN 23 of 53 DIED (43 %; was 39 %). 11 of the 23 are the geom posts of class S1; 6 have "log none" |
| N1 repeating lines | SAME | V: ADOPT-GUARD 24, NO-ROW-SOURCE 16, ITEM-SYNC phy_serdes_b 9, HOLD-TERM (QC 17, KV 12 holds without owner or eta), CONFIG-KEY-UNREAD, PLAN-CONFIG-DRIFT every tick |

## Classes, ranked by fleet hours

### S1. A flow fix on main does not reach work in flight. Largest.
- Count (V/R): 17 geom-stage DIED posts (11 NO-PATTERN, 2 GEOM-FAIL), 10 of them after the fix reached the hub rt.
  HOLD-DONE 7ed394df813 applies to new kits only (R): the extra hold chunks cost 76.2 kit-hours in the last 24 h,
  about 6 kit-hours per 2 h, and every running kit keeps them. Drivers older than 36d0a6df8f6 still stop after geom
  and are resumed by hand (R, COORD). Trend: new as a class; C1 at 0600 was one instance.
- Root cause: a kit, a private spec and a run-item driver each copy their tools once (`.geom-tools-<hash>`, kit
  snapshot, the driver's own rt). Control scripts (exit codes, stop rules, goal handling) sit in the same copy as the
  tools that shape the result, so a control fix needs a new kit. Nothing lists what a fix did not reach.
- Structural fix (P): split the copy in two. Result tools stay pinned and hashed. Control scripts (geom_check.sh rc,
  hold_guard stop rule, goal table, resume logic) are read from rt/current at each stage start. `ot-push-main` on a
  commit marked FLOW-FIX writes FIX-REACH.tsv: every live kit, spec and driver that predates it, by owner lane.
- Owner: FLOW-OPS-R2. Core-h (I): 80 to 130 (6 kit-hours of hold chunks at 8 to 16 threads, plus stopped kits waiting
  for a hand resume).

### F1. Threads committed at 417 % of cores.
- Count (V): load 1.17x fleet-wide; epyc2 490 threads / 128 cores, epyc8 498 / 96. Trend: better (1.45x).
- Root cause: admission charges memory by measured stage peak but CPU by nothing (THREAD_CAP_FACTOR 0); the load cap
  acts after the host is already over.
- Structural fix (P): charge CPU the way memory is charged: p90 measured cores of the stage class, summed per host,
  admit while the sum is under the core count. No new cap value; the existing queue holds the rest.
- Owner: FLOW-FLEET-R2. Core-h (I): 70 to 110 (5 to 8 % time-slicing loss at 1.17x).

### P1. A queued kit is staged, times out, is called "killed", and is staged again elsewhere.
- Count (V): 183 REQUEUE, 80 RESTAGE + RETRY-HOST (2 items twice), 57 orphan waiters, in every tick. 50 requeues are
  lane jobs pinned by --dir (FAM-S81-COL-H9R0-R4 10, OPUS-FIX-HEAD-LEP0N-R8 6, FAM-S81-MISC-R4 5). Probes queued
  for hours (R, COORD); COL-H10-R4 got its probe through by resubmitting unpinned (R, 06:23). Trend: new in this form.
- Root cause: the tree is copied to a host before the host admits the job, so the job is tied to that host. After
  600 s the client gives up, the wave reads a waiter that never started as a killed attempt, picks another host and
  copies again. Small measurement jobs wait in the same line as 48 GB kits.
- Structural fix (P): admit first, stage after: one fleet ticket that keeps its age across hosts, and the copy starts
  only when a host has admitted it. A waiter that never started is not an attempt. Jobs of 4 threads / 16 GB or less
  use a separate small-job line per host, so a probe never waits behind kits.
- Owner: FLOW-FLEET-R2 (ot-run), WAVE-OPS-R1 (wave restage). Core-h (I): 30 to 60 direct (80 copies and relaunches,
  kit_wave_step 355 to 746 s per tick); calendar: 10 to 25 min per restaged kit, hours per pinned probe.

### T1. rt/current moves every 7 min; bind and gen of one batch land on different tools.
- Count (V): 16 hub rt moves in 108 min. 18 FAIL bind_toolskew at 07:36 (bind of record 06:44, reset_anchor.py
  differs; the message prints "tools ?, rt ?"), S81 class breaker open. KV TOOL-SKEW WARN 428 of 19,004 modules
  differ from pin 47a226faaa96, 10 lines. efe70f16d3 broke every private-spec `--bind-out` on the hub rt from 06:49
  until its fix (R, FLOW-STRIPBODY-R2 06:53). 1 push died on tests (07:11). Trend: up.
- Root cause: gen takes the reset / relay generators from rt/current at launch, the bind took them at bind time, and
  rt/current follows main with no trial run. The skew is found after launch and counted as a failure of the row.
- Structural fix (P): the bind record stores its rt sha, and gen runs the reset / relay generators from that rt (it
  is on disk under rt/<sha>): the skew cannot occur. Until then BIND-GEN-TOOLSKEW queues one rebind per bind of
  record and re-arms its rows, and does not count toward a class breaker. rt/current moves only after one
  private-spec dry run passes on the new rt.
- Owner: FLOW-OPS-R2 (rt pin, dry run), WAVE-OPS-R1 (rebind in place of FAIL, close the S81 breaker).
  Core-h (I): 10 to 20 direct; at risk: S81 wave launches stopped from 07:36 until a rebind.

### L1. plan_gate_pre and the strict bind disagree on LANDREMAP.
- Count (V/R): 4 DIED on "FAIL LANDREMAP slw_su_l1__cla2a78701" after 2,561 to 2,939 s each; one tree run of 2 h CPU
  ended with 44 findings, all LANDREMAP (R, FAM-QC-SLWSLE-R1 06:40); the strict bind accepts the same plans (R,
  COORD). QC wave: 0 launches for 123 min (V, NO-PROGRESS 07:27). Trend: new.
- Root cause: the check and the bind each carry their own rule for a landing reset reference; no test runs both on
  one plan; a finding has no declared weight.
- Structural fix (P): one predicate module imported by both. Every finding class is declared BLOCKING (bind refuses
  it too) or ADVISORY (rc 0, listed). A fixture test per class fails when the two disagree. For LANDREMAP the gate
  runs landing_remap.py on the named types and re-checks, in place of a FAIL.
- Owner: new Sonnet lane. Core-h (I): about 6; calendar: 45 min to 2 h per QC chain.

### A1. A view-repair tool shipped as a standard step without a control.
- Count (R): abstract_pin_stub.py raised EOL violations 96 -> 1,348 on a view heavy with pin-in-OBS (COL-H10-R4
  control). KV overlay ROWS-READY 07:18, withdrawn 07:36; S81 PUSH2 (21 LEFs) staged as provisional. Trend: new.
- Root cause: the tool writes its output without comparing the defect count before and after.
- Structural fix (P): the tool counts its own defect classes on input and output and refuses to write a LEF that is
  worse in any class; one pin-in-OBS-heavy fixture in the tests. A row built on a tool output names the control run.
- Owner: new Sonnet lane (with the COL-H10-R4 bisect). Core-h: 0 lost (caught before any cut); at risk 24 LEFs.

### K2. Disk alert names no writer.
- Count (V): epyc10 scratch2 520 -> 259 GB in 64 min; DISK-RATE state 2 at 07:10 ("floor in 1.7 h"), holders none,
  AUTO-RETIRE deleted 0. State 1 on epyc8 (299 GB/h) and intel2 (87 GB/h). Lane-quota alert: kw43-wave on intel1
  37 GB in 1 h. EPYC10-DISK-R1 has no post yet. Trend: same class as A1 at 0350, new host.
- Root cause: the rate monitor measures the disk, not the units; finding the writer is hand work every time.
- Structural fix (P): at state 1 or higher disk_rate.py adds the top 5 writers to the alert, from the write-byte
  counters of the ot-run units (cgroup io.stat) mapped to lane and dir. Admission uses projected free space
  (free minus rate x 1 h), so a host near the floor stops taking new kits by itself.
- Owner: EPYC10-DISK-R1 (writer now), FLOW-FLEET-R2 (alert + projection). Core-h: 0 lost; at risk 49 units on epyc10.

### C2. `ot-run --cancel` cannot find the unit.
- Count (V): 15 cancels in the hub log: 4 "(no client)", 11 cancel-dir DEAD-CLIENT; lanes fall back to exact-PID
  stops (R, COL-H10-R4 06:23). Trend: same.
- Root cause: cancel looks for the live client process; a unit whose client is gone or sits on another host has no
  entry.
- Structural fix (P): ot-run writes unit id, host, dir and lane to a hub ledger at submit (as the wave launch
  journal does); --cancel resolves by unit, dir or tag from the ledger and stops the unit on its host.
- Owner: FLOW-FLEET-R2. Core-h: under 5.

### D1 / N1 / E1. Unchanged.
- D1 (V): NO-PATTERN 43 %. Fix (P): ot-run always writes a default log; the DIED post takes the stage's own verdict
  line when one exists. Owner FLOW-FLEET-R2.
- N1 (V): also s81_head 0 launches for 431 min (NO-LAUNCH x24), STUCK-STATE 21 rows (S81 1, QC 10, HEAD 10),
  NO-ROW-SOURCE 26 QC + 14 S81 items that "can never launch", ARCHIVE FAILED 3054c87a89d6 (x34). Fix (P): a line
  identical for 6 ticks becomes one OWNERS row and is then printed only when it changes. Owner WAVE-OPS-R1.
- E1: land the OT_UNDER_TEST guard; tests write signals to a temp log. Owner FLOW-OPS-R2.

## Requests to COORD (ranked)

1. T1 now: WAVE-OPS-R1 rebinds S81 J7 on the current rt, re-arms the 18 rows and closes the breaker.
2. S1: control scripts read at stage start + FIX-REACH.tsv per FLOW-FIX push (FLOW-OPS-R2). Until then each lane
   with a spec made before 07:14 treats a geom rc 1 with a verdict line as advisory.
3. P1: admit first, stage after; small-job line (FLOW-FLEET-R2).
4. F1: CPU charged by measured stage class (FLOW-FLEET-R2).
5. T1: gen uses the generators of the bind's rt; dry run before rt/current moves (FLOW-OPS-R2).
6. L1 and A1: one new Sonnet lane each. K2: writer names in the DISK-RATE alert.
7. C2, D1, N1, E1 as above.
