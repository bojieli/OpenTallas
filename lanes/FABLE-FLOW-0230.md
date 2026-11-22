# FABLE-FLOW-0230: procedural / flow review, window 11-22 00:26 to 02:35 PST

Lane FABLE-FLOW-0230 (Fable 5.2). Read-only review of process and tooling. Nothing cancelled, signalled, launched,
deleted or edited except this file and one RESULT line. Previous: lanes/FABLE-FLOW-2200.md (11-21 19:45 to 21:48).
Sources: autopilot/log.txt (738 timestamped lines from 00:26), lanes/FLOW-HEALTH.tsv (02:07), `failure_breakdown.py`
(02:31), `ot-run --status` (02:30), ~/.local/state/ot-run/signals.log, lanes/posts/*.md (418 posts in the window, 85 DIED),
8 death logs read on the hub, `ps` on all 7 hosts (02:36) for the runtime (rt) sha in use, rt/current = main bac6bcfd79b3,
autopilot/kit_wave.json, tools/autopilot/repeat_stop.py.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Not done: per-attempt wall time of wave kits was not measured from the kit dirs (launch-to-verdict pairing in the log gave
a median of 116 min, used as an estimate); the 75 SKIP-HELD rows were not read one by one; the untimestamped tracebacks in
autopilot/log.txt cannot be dated and are not counted. "Share" = estimate (I) of fleet thread-hours in the window
(624 cores, about 1,550 threads committed) unless marked.
Limit: all models were 429 from 01:4x to about 02:1x; 41 lanes posted RESUMED from 02:18. Launches did not stop
(autopilot is not an LLM): 4 launches 01:30 to 02:00, 4 after 02:00.

## Headline

1. **19 of the 29 kit verdicts in the window are one stop, PLACE-SETUP-STOP, and 14 of them are one path** (V): QC cb
   family, lockup latch `u_lk_nk_..n_b/q[372]` to `u_t01`, 3.2 um, 2 stages, wns -380.5 to -380.9 ps. 29 runs on this one
   path since 11-21 13:27 across 15 variants. The repeat guards are per item and per type, so each variant spends its own
   attempts (class R1). The fix for the cause exists as a V4 plan row (CLASS-SWEEP-R1 class A, 02:21), not applied.
2. **Fleet 57 to 68 % busy with 187 to 194 rows not launching** (V, UNDER-USE 02:02 to 02:17): SKIP-HELD 75, q_running 46,
   WAIT-FORM 42, q_fail 11, KW-FIX-45 8. S81 has 274 type rows held for the J7 apply (timer 04:14, R). 15 launches in 2 h.
   Load is uneven: epyc10 102 to 147/96 and epyc9 103/96 while epyc8 36/96 and intel1 42 to 52/112.
3. **Die binds: 18 died, 10 finished** (V): 99 thread-hours in dead binds. Three ran 1.9 to 3.0 h and failed at EMIT or
   compare; 7 were cancelled by their own lane as doomed. Five pre-bind checks landed in the window (class B1).
4. **Known class (a) is a label error, not an admission refusal** (V, confirms FLOW-FLEET-R1 02:22): see K-a.
5. **Hub scratch is at 96 %, 166 GB free** (V 02:36), fell 81 to 159 GB/h (R, FLEET-OPS-R), 3 auto-retire passes deleted 0,
   3 lane jobs already refused on the hub with disk-ETA hold (class A1).
6. **63 % of running processes that name a runtime tree are below the floor 6d2e187f0d** (V): 210 of 335, 33 of 43 rt
   versions. Most started before the floor existed (01:26). Five lanes started work on a below-floor rt after it (class T1).
7. **Count: signed any plan 548 / current plan 438 (V 02:31)**; was 527 / 431 at 21:43. 3 SIGNED verdicts in the window.

## What FABLE-FLOW-2200 asked for: state now

| 2200 item | State at 02:35 |
|---|---|
| H1 WAIT-VISUAL holds routes | FIXED (V): `review_before_route.required` absent on all dies; log says "VISUAL-PENDING ... (advisory)"; the bucket is gone from UNDER-USE (was 51) |
| H2 hand-set host cap, no owner or expiry | FIXED (V, HOST-REPORT): epyc7 LOAD_CAP_FACTOR=1.2 owner FLOW-FLEET-R1, expires 11-23 06:00Z; 0 "not admitted" lines in signals.log in the window (was 31) |
| H3 unsignable GRT runs keep running | FIXED (V): GRT-ARM CANCEL acted on 6 QC units at 02:02 to 02:04 (3.7 h jobs), reason and owner in the line |
| H4 cancel by pattern | PARTLY (R): `--cancel --reason`, manual cancel takes no free retry. Unit id or exact dir still not required |
| A4 raw tree copies | NOT fixed (R): QC-PLAN-R13 chains "cp -a takes about 80 min" on epyc10 at load 96/96, 6 chains |
| C2 superseded ENQUEUED rows | Down: 9 to 10 superseded-event rows (was 34); RETIRE-SUPERSEDED finds 0 to 1 stale per pass |
| C4 repeat ledger | NOT landed (V): "8 earlier attempt(s) not in the ledger" on two S81 rows that reached 9 attempts |
| 1900 (g) parked die still alerts | NOT fixed (V): see N1 |
| TOOLS-LAG / r708 | NOT landed (V): QC 526 commits and S81 331 commits behind, both "missing r708" (QC was 522 at 02:13) |

## Known open classes (confirm and measure only)

**K-a. "geom stage dies on admission refusal".** Count 9 DIED in the window (V; FAM-KV-HROOT-R1, FAM-S81-COL-H10-R4,
FAM-S81-DSDV-R1, FAM-S81-SLICE-R6, HEAD-CTL-R1, OPUS-FIX-HEAD-LEP0N-R8, OPUS-FIX-KV-HUB-R6, OPUS-FIX-QC-COLL-R3 x2), 21 to
712 s each, 4.5 thread-hours. Not a refusal: "admits N GB (... headroom 0 ...)" is the first information line of every
ot-run log (V in 8 of 8 logs read, including binds that ran 3 h). In the log read in full the unit was admitted after 1 s
and exited 1; the log has 5 lines and the tool error is not in it. The death classifier quotes the first `ot-run:` line
when it finds nothing else. Real refusals in the window: 0 memory, 3 disk-ETA on the hub (A1). Root cause: the geom stage
writes its error to a file the live log does not include. Fix in progress (R, FLOW-FLEET-R1: DEATHCLASS GEOM-FAIL/ADMIT;
its push died rc 3 at 02:21, retry running). P: the classifier must never use an `ot-run:` / `ot-heavy:` information line
as a cause; a log of under 10 lines with rc != 0 = class NO-OUTPUT with the stage error file path. Share: under 1 %.

**K-b. R8 table not re-derived.** 3 binds died in the window (V, FAM-KV-IOPC-R4, 1445 + 380 + 388 s, "RC_ELAB 0"; R: 30
R8_STALE on the 32 pc_v3 pi bundles). Three lanes run their own bind, refresh, rebind loop (R: QC bind_v2.sh,
FAM-QC-CB-R4, FAM-S81-COL-H10-R4). Landed 02:27 main 7516d11ccf2: plan_gate_pre R8STALE refuses before the bind. That
makes the class self-stopping. Not yet impossible: P one `bind --r8-refresh` in main so the three private loops go.
Share: about 1 % (0.6 h x 8 threads, plus one extra bind per lane loop).

**K-c. landing_remap on port-pad relay chains.** 1 death in the window (V, OPUS-FIX-KV-HGI-R6, RemapError "tree relay
after a non-tree stage"). Landed 01:49 main e8a66236b2 (R: identity pass, 16 of 16 rewrites equal the hand receipt;
LANDREMAP 0 on R6f and R6g). New sub-class from the same post: a second landing_remap run on an already remapped plan
with the old base flips a density tap (clk_t111 back to t110). P: landing_remap stamps the plan with the base sha it
remapped from and refuses a second run from the same base. Owner FLOW-OPS-R2. Share: under 1 %.

**K-d. lockup_regions inert in a real bind (KV hg/hgi).** Still open at 02:27 (R: "rest" region of 40 loads on all hg/hgi,
cause under debug). 0 deaths and 0 builds on it in the window (V); 19 types stay held; D28 hand-off posted with the item
marked KNOWN. Risk only: D28 applies and the 19 types stay held. Owner OPUS-FIX-KV-HGI-R6. Share: 0.

## Classes, ranked by fleet hours

### R1. One cause fails across a family; repeat guards are per item. Largest waste.
- Count (V): PLACE-SETUP-STOP verdicts per hour since 11-21 12:00: 4, 3, 3, then 9 (22 h), 13 (23 h), 5 (00 h), 14 (01 h),
  4 (02 h, part). 55 in all; QC cb 34 (29 at -380 ps, 15 variants), S81 slice_station 6, KV kv3_pc 5 (-657 / -660), QC
  slw_st 3. In the window 19 of 29 verdicts. Trend: rising since 22:00.
- Root cause in the tool (V, repeat_stop.py gate()): (1) the fingerprint is per item, so 15 cb variants each get 3
  attempts; CAUSE-CAP is per type stem, so cbf_q00, cbf_q01, cbn_q00 ... each get their own. (2) A PLAN verdict at `place`
  does not set `plan_input`, so a changed tools hash releases the stop. Main took 37 commits in the window, so every
  BLOCKED-REPEAT is released within minutes: 4 "REPEAT-STOP RELEASE ... inputs:tools" at 01:32 and 02:01, 3 minutes after
  the stop; 2 relaunched (cbn_q11 attempt 4, cbn_q00 attempt 5), 2 were caught by CAUSE-CAP. (3) The ledger misses old
  attempts, so the cap of 9 was reached on slice_station t6 / t29 with one cause.
- Structural fix (P): a cause key for STRUCTURAL place and GRT stops = die + start cell class + end cell class + wns
  bucket (here: lockup latch to u_t01, -380). Two distinct items with the same key hold every row whose plan block has
  the same construct, as one hold with one owner line, released by a changed plan block or a named fix sha. Set
  `plan_input` for every verdict of class PLAN / STRUCTURAL at any stage, so a tools change never releases it.
- Owner: FLOW-OPS-R2 (repeat_stop / kit_wave), FAM-QC-CB-R4 and QC-PLAN-R13 (apply the V4 row).
  Share: 10 to 15 % (I: 19 runs x 8 threads x about 1.5 h of about 1,550 committed threads x 2 h).

### U1. Rows that cannot launch while 35 to 43 % of cores idle.
- Count (V): idle 252 to 275 of 624 cores; rows not launching 187 to 194. Trend: was 198 rows and 42 % busy at 21:42, now
  57 to 68 % busy. Launches per hour (FLOW-HEALTH): 14 (22 h), 13 (23 h), 10 (00 h), 11 (01 h).
- Root cause: holds, not capacity. 274 S81 + 40 KV type rows wait for a plan event; WAIT-FORM 42; SKIP-HELD 75 whose
  reasons are not printed per bucket (one line in 2 h names a KV-PLAN-R6 hold from 11-21 19:1x). kit_wave.json keeps
  about 200 `*_prev_*` / `*_released_*` hold keys of past events beside the live ones (live: s81 344 + 40 route, hbm 107,
  kv 12, qc 4 + 10 route), so the live set is hard to audit.
- Structural fix (P): UNDER-USE prints SKIP-HELD split by hold key with owner and age; a hold without owner + release
  term older than 24 h is listed by name every tick. Move the historic hold keys out of kit_wave.json into a log file.
- Owner: die owners for the holds; FLOW-OPS-R2 for the report. Share: about 35 % of cores idle; not all recoverable.

### B1. Die binds that fail late, or are cancelled as doomed.
- Count (V): 28 bind units ended in the window: 10 DONE (16.7 h), 18 DIED (99 thread-hours). Late failures: FAM-S81-
  COL-H9R0-R4 3.0 h then compare FAIL (361,869 mismatched); OPUS-FIX-S81-SVC-R9 2.0 h then "EMIT relay_depth ... 1 row
  matched no internal sink"; FLOW-STRIPBODY-R2 1.9 h then "EMIT clock landing: expected exactly one bound instance";
  FAM-QC-SLWSLE-R1 1.5 h. Cancelled by the lane: 7 (QC-PLAN-R13 3 binds at 1.5 to 2.3 h, doomed by a coll_core EMIT).
  Refused in seconds (good): KIT_TOPOLOGY_BIND_STALE x2 (7 s, 15 s).
- Root cause: bind validates in elab order, so a one-row EMIT error surfaces after the elab. One bad row costs 2 to 3 h.
- Landed in the window (R, FLOW-OPS-R2): ISTCYC + reprice (fda4eaad0e), DEADIN (16811af012), TAPNAME + BIND_STALE
  (6d2e187f0d), LANDREMAP (e8a66236b2), R8STALE (7516d11ccf2). Self-stopping for those five causes.
- Still open (P): the two EMIT forms above have no pre-check. Run every EMIT rule that needs only plan + as-built names
  (relay_depth sink match, clock landing instance count) in plan_gate_pre. For the rest, bind prints all EMIT / compare
  errors of types already elaborated every 15 min, so a lane can stop at the first one.
- Owner: FLOW-OPS-R2. Share: about 6 % (99 thread-hours).

### T1. Work started on a runtime below the floor.
- Count (V, ps 02:36): rt below 6d2e187f0d: 33 versions, 210 processes; at or above: 10 versions, 125 processes. Started
  after 01:26 on a below-floor rt: QC-PLAN-R13 (33fe1ccf0716 and 6dbb162ffe89, 6 chains from 01:52), FAM-S81-SERDES-R7
  and kw45 (404887a342b0, the sealed J7 pin), OPUS-FIX-S81-COLROM-R6 (06b2ca5293cd), FAM-S81-COL-H9R0-R4 (5a966bb45bcf),
  S81-J6-ASSEMBLY-R5 J8 candidate (f66d2a090e69, declared). The QC-PLAN-R13 chains fix a tap rename (clk_t130 to
  clk_t126), the case TAPNAME checks in seconds.
- Root cause: the floor is a sentence in posts. Lanes pin an rt per tree and nothing compares the pin with the floor.
- Structural fix (P): `min_rt` in kit_wave.json; private-spec, ot-build and `ot-run --plan-job bind` refuse an rt that
  is not a descendant of it (override flag, logged); the tick prints the units below it by lane.
- Owner: FLOW-OPS-R2. Share: at risk, not spent: 6 QC binds with ETA 04:30 to 05:00.

### A1. Hub disk near the floor; alert has no actor.
- Count (V/R): intel2 scratch2 166 GB free of 3.5 TB; DISK-RATE 01:00 276 GB, 01:42 194 GB, 02:20 189 GB; AUTO-RETIRE
  "deleted 0" 3 times; top writer fix-sync-s81 56 GB/h; lane-quota alerts on kw45 intel1 (171 to 231 GB) and epyc2
  (284 GB) x5, "alert only". 3 units refused (NOT-RUN disk-ETA hold: FAM-S81-COL-H10-R4 place, OPUS-FIX-HEAD-LEP0N-R8,
  OPUS-FIX-S81-COLROM-R6). The death class printed for them is SSH-DROP (label error).
- Root cause: sealed place picks the hub as a build host; the retire pass finds nothing because the writers are live lanes.
- Structural fix (P): the hub is not a candidate host for kit stages while free < 300 GB (computed, like the drain); the
  quota alert names an actor: no new admission under that lane dir until it posts a size plan.
- Owner: FLEET-OPS-R, CLEAN-AGGR-R3. Share: under 1 % now; a hub at the floor stops binds and the autopilot state writes.

### D1. Death classes that say nothing: 28 of 85 (33 %).
- Count (V): 9 admit-line (K-a), 11 with no class at all (45 h wall, 468 thread-hours; includes two 7 h GRT runs of
  FLOW-CLKGRT-R2 that ended DPL-0036 and the 3 late binds), 5 "rc N, no log", 3 SSH-DROP that are NOT-RUN refusals.
  FLOW-HEALTH "by class" still shows UNCLASSIFIED in every hour from 21 h to 23 h.
- Root cause: the post hook classifies from the live log tail; long jobs write the verdict line (FAIL_route, EMIT,
  verdict JSON) to a log it reads but has no pattern for.
- Fix (P): add the 4 patterns seen here (FAIL_route make exit, EMIT, `"verdict": "FAIL"`, NOT-RUN <reason>); a DIED
  post without class= is not posted, it is posted as class=NO-PATTERN with the last non-ot-run line.
- Owner: FLOW-FLEET-R1. Share: 0 direct; it hides B1 and K-a from the hourly count.

### N1. Checks that fail every tick and escalate to no one.
- V: ITEM-SYNC qwen_compute/phy_serdes_b to epyc2 rc=2 "self-heal FIX-SELFCONT": 15 today, 121 since 11-17.
  NO-ROW-SOURCE "can never launch": QC 26 items, S81 14 items, 8 lines each. Parked HBM: 90 log lines in 2 h, 12
  ADOPT-GUARD alerts after 02:00, bind preflight "UNKNOWN (fail closed)" on two missing plan files 24 times, although
  `dies.hbm.parked` is set (V). SKIP-SAME-INPUT hd_host_n and kv3_io_cor_v1 (correct, self-stopping). STALE 2: S81
  slice_station__t52 SIGNED, count pending 23.5 h; iqf__t1 ROUTE-HELD 22 h. HUB-SYNC-FAILED 5 alerts (OWNERS-SWEEP.tsv
  from 23:57, a KV-PLAN-R6 post 01:34, NOPROG-ACTIONS.tsv 02:02); hub tree is clean at 02:36.
- Fix (P): a tick line repeated unchanged for 24 h becomes one OWNERS row (owner = the lane named in the fix text, else
  FLOW-OPS) and is printed once per hour; ADOPT-GUARD, bind preflight and src_overlay skip a parked die.
- Owner: FLOW-OPS-R2. Share: 0.

## Push and merge

ot-push-main in the window: 23 rc 0, 1 died (rc 3, 10 s) (V). Was 32 / 4 in the 2200 window. 37 commits reached main.

## Requests to COORD (ranked)

1. R1: hold the QC cb family on the live plan until the V4 tap[0] row is applied (QC-PLAN-R13); FLOW-OPS-R2 to set
   `plan_input` for PLAN / STRUCTURAL verdicts at every stage and add the family cause key.
2. U1: print SKIP-HELD by hold key, owner and age.
3. B1: EMIT name checks in plan_gate_pre.
4. T1: `min_rt` enforced by the tools; tell QC-PLAN-R13 that its 01:52 chains run below the floor.
5. A1: take the hub out of the kit-stage host set under 300 GB free; name an actor for the quota alert.
6. D1 and N1 as above.
