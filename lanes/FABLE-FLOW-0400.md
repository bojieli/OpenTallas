# FABLE-FLOW-0400: procedural / flow review, window 11-21 01:43 to 03:43 PST

Lane FABLE-FLOW-0400 (Fable 5.2). Read-only review, process and tooling only. Nothing cancelled, signalled or launched.
Previous: lanes/FABLE-FLOW-0200.md.
Sources: autopilot/log.txt (1,136 lines in the window; 11-20 12:00 onward for trends), autopilot/kit_wave_state.json and
kit_wave.json, lanes/FLOW-HEALTH.tsv (03:08), tools/failure_breakdown.py (run 03:45), `ot-run --status` (03:5x),
kit_wave.py in rt/42fa174c1809, the coll_ftc attempt_5 kit dir on epyc2, CODEX-LOG handoff 03:32, handoff FLEET-WATCH-R4.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Fleet base: 310 running units (V), so 620 unit-hours in the window.

## Headline

1. **The coll_ftc report is wrong on mechanism, but running attempts ARE being stopped by the wave on another path (V).**
   - coll_ftc attempt_5 (event N46R4A4) was not killed. At the 20:12 plan switch it got SWITCH-SUPERSEDE-KEEP and REKEY
     ("plan block unchanged, keeps running"). It ended by itself at 01:34 after 7.3 h: `FAIL_route [ERROR DRT-0255] Maze Route
     cannot find path of net ...dch[10].u_dsel/net158717`, 2 h 10 min into detail route, job rc 2, no signal line. The wave
     launched attempt 6 at 01:46. The 03:18 line is attempt 6 passing auto-GEOM and being queued for route.
   - pv39aac7a1 (slw_hc3) was a RESTAGE: gen unit launched 03:13:14 on epyc7, stopped 03:19:52 (6.6 min old), relaunched 03:20.
   - Plan-event supersede does not stop running rows: since 11-20 18:00, 67 SWITCH-SUPERSEDE-KEEP, 46 REKEY, 34 SUPERSEDED-KEEP;
     4 CANCEL-SUPERSEDED lines, all with `units []`. The owner rule holds on that path. FLEET-WATCH-R4 reached the same result.
   - **The path that does stop running work is `reap_stale_attempts` case 1, "superseded by attempt N of the same item"
     (kit_wave.py:15695-15733, KW-FIX-45).** Since 11-20 12:00: **62 live attempts stopped; 54 have a measured age, sum 88.5
     unit-hours** (about 1.9 percent of the fleet over 15.7 h). In this window 1 (s81 dsdv_slice_c1x_C__t8@4, 0.9 h); 5 more at
     01:15-01:34 (6.9 h, one of them 4.8 h old). coll_ftc itself was stopped this way twice on 11-20: @1 at 15:54 (1.7 h in
     route) and @4 at 16:12 (3.6 h). Detail in class (b).
2. **The 0200 headline class is fixed (V).** Design stop filed as infra-oom: 36 classifications and 36 EARLYOOM-RESUBMIT lines
   up to 02:35, none after; from 02:4x the same stops read `STRUCTURAL place-setup-stop` (22). Codex 8db2fc6 / 9abebc (R).
3. **The 16 unsplit S81 svc units were stopped at 01:58-02:02 (V)** by STRUCT-STOP (owner OPUS-FIX-S81-SVC-R5), 8 to 11 h in.
4. **Sign-off count: 493 any plan, 408 current plan (V), +1 / +1 since 01:59.** STALE 106 (0200: 111).
5. **Disk: epyc9 scratch 158 GB (427 at 02:00), intel1 161 GB, epyc2 217 GB (V).** No refusal line yet.

## The 0200 fixes

| 0200 item | State (V unless marked) |
|---|---|
| (a) STOP marker before gate-lost; earlyoom needs a kill record | Landed about 02:38. 0 infra-oom after; 22 place-setup-stop STRUCTURAL. |
| (b) svc split owner; over-400k representative first | 16 svc rows stopped by STRUCT-STOP. Reps-first pushed 18ff3f60c2 (R, FLEET-WATCH-R4). |
| (c) RETRY-INFRA-STOP inherits no older hold | Pushed in 18ff3f60c2 (R). 2 rows stay on deliberate hold_items (R). |
| (d) GRT booked as 2 threads | Not done. Threads granted 2,677 on 752 cores (0200: 2,514). |
| (e) epyc9 reclaim names the blocking container | Not done. 7 DELETE deferrals on epyc9 (0200: 13). |
| (f) s81 pin as a sha; KV r708; QC `__pv` rows | Not done. TOOLS-LAG s81 still "bad revision j5tree" (eighth review). |

## Classes, ranked by fleet time wasted in the window

### (a) Design stop classified as infra-oom, resubmitted: FIXED

- Count and trend (V): 36 resubmits (22-23 h: 107, 00-01 h: 85, this window 36, after 02:38: 0).
- Fleet time (I): about 14 job-hours, 2.2 percent, at the 0.38 h per resubmit measured in 0200; now zero.
- Residual (V): slw_st_b_v1__cle6023ec2 was on resubmit 2/4 at 02:33 for a wns of -106,079 ps. Check that jobs resubmitted
  before 02:38 end as place-setup-stop and are not resumed. Owner: FLEET-WATCH-R4.

### (b) A newer attempt of the same item stops the older live one (NEW evidence)

- Count and trend (V): 62 since 11-20 12:00. By hour block: 12-13 h 6, 15-17 h 37, 18-20 h 14, 01-02 h 6. Stopped units:
  47 `kw-` wave units (gen and place, 19 of them with a live `kwp-` place service) and 9 `ap-` queue jobs in route. Ages
  0.1 to 7.3 h (svc_lo_dsdv_svc_rs__t6@1 7.3 h; c1x_C__t6@4 4.8 h; svc_lo t5@2 4.1 h; slw_st_b_v1@9 4.0 h in route).
- What launched the newer attempt while the older was live (V, the item's lines in the hour before each stop):
  RESTAGE / RETRY-HOST about 25, INFRA-FREE-RETRY after an outside `ot-run --cancel` 8, HUNG-WATCH CANCEL 5, FLOW-REGEN 6,
  RELAUNCH-ON-FIX 2, no visible trigger 12.
- Example chain (V), s81 dsdv_slice_c1x_C__t8: 01:03 attempt 3 is cancelled from outside while waiting in geom_run and gets
  INFRA-FREE-RETRY; 01:05 attempt 4 launches; 01:14-01:17 attempt 3's GEOM result arrives anyway and it is submitted to route;
  01:34 the reap stops attempt 3's route job "superseded by attempt 4"; 01:36 attempt 5 launches; 02:00 the reap stops attempt 4
  (55 min in) "superseded by attempt 5". Three attempts, none allowed to finish. svc_lo_dsdv_svc_rs__t2 went @2, @19, @20 in
  32 minutes on 11-20 20:25-20:57.
- Root cause: two defects that feed each other. (1) Five launch paths create attempt N+1 from a FAIL / RETRY-INFRA mark without
  proving attempt N is dead (hub unit, place client, queue job, container). (2) The reap settles two live attempts by start
  time: it keeps the newest and stops the one that has done the work. The code comment at 15729 records the same class once
  before (FLOW-1949: "13 live jobs stopped in 2 h"); that fix narrowed the condition and kept the rule.
- Structural fix (P): (1) one launch guard used by every relaunch path: if `_row_live` is true for any attempt of the same
  item and event, log LAUNCH-KEEP and do not launch. (2) In the reap, the survivor is the attempt with the most progress
  (`heavy_progress`, then stage, then start time); the unstarted newer one is cancelled. (3) Test: replay the 62 cases from the
  log; none may stop a row past place admission.
- Owner: FLEET-WATCH-R4 (already on the supersede report; this is the path it should take, not SWITCH-SUPERSEDE).
- Fleet time: window 0.9 unit-hours (0.15 percent); 6.9 h in the 30 min before it; 88.5 h in 15.7 h, about 1.9 percent, in bursts.

### (c) Long builds relaunched with no named fix; attempt caps that count attempts, not causes

- Count (V): coll_ftc ran 7.3 h to DRT-0255 (STRUCTURAL drt-nopath) and was relaunched 4 minutes later on the same plan block
  and src. SKIP-SAME-INPUT did not hold it because 32 kit flow files differ (latch_restore, postplace_setup_stop, cts/grt
  hooks); none is named as a fix for the route failure. 12 items reached BLOCKED-CAP in the window at 6 to 17 attempts
  "mixed errors" (svc_lo_dsdv_svc_rs__t1 17, ot_s81sl_leaf__t28 10, 5 KV kv3_hgi/pv rows 6-7). 18 CRASH lines carry no cause:
  8 `route-make-fail: FAIL_route make exit 2 (see run_route.log)` (7 of them KV) and 10 `flow-error: exit 6`.
- Root cause: the full-input hash includes every flow file, so any flow refresh releases every stopped item, whatever it failed
  on. The cap counts attempts across causes, so six different procedural deaths look like one design that fails six times, and
  a design failure seen once gets five more tries. The classifier stops at the make exit code.
- Structural fix (P): (1) a STRUCTURAL result after detail route starts (drt-nopath, routed-not-signed) holds the row for the
  die owner like STRUCT-STOP, released by a changed plan block or a named `fix=` key, not by a flow refresh. (2) The classifier
  reads the first `[ERROR ...]` line of run_route.log into the fail key. (3) The cap is per fail key: 2 for a design key, the
  infra budget for infra keys. Test: replay the 12 capped items.
- Owner: FLOW-HEALTH-1 (classifier, cap), FLOW-GRT-RESID (drt-nopath hold).
- Fleet time: coll_ftc a6 2 unit-hours so far (0.3 percent), 7 h if it runs to the same end. The KV route rows not measured.

### (d) Oversized types running long

- Count (V): 16 svc units cancelled 01:58-02:02 (class resolved; about 4 unit-hours inside the window, 0.6 percent; 150 h sunk
  before it). Still silent with CPU growing: ot_s81sl_kv_leaf__t2, two rows, 989 and 778 minutes.
- Root cause and fix: as 0200 (b). Reps-first is on main (R). Remaining gap (P): HUNG-WATCH silent over 8 h on an over-cap type
  posts one NEEDS-OWNER line with stage and cell count.
- Owner: FLEET-WATCH-R4. Fleet time: 4 unit-hours (0.6 percent) in the two kv_leaf rows; whether they can sign is not measured.

### (e) RESTAGE of fresh waiters

- Count and trend (V): 6 in the window (11-20 20 h: 20; 21-23 h: 19; 00-03 h: 16). 69 in 10 h, each redoes kit_rtl and gen, and
  each is a feeder for class (b).
- Root cause (V): kit_wave.json top level has `restage_min_wait_s: 300`, `restage_max_per_tick: 1000`,
  `restage_place_waiters: true`. The 300 s value is the KW-FIX-40 temporary setting of 11-08 ("revert after the waiters
  drain"); the note of KW-FIX-42 says it was reverted to 1800, the live value says otherwise. pv39aac7a1 moved at 398 s.
- Structural fix (P): temporary config keys carry an expiry (`<key>_until`), and the wave logs and ignores an expired
  override; set 1800 back through kit_wave_edit now.
- Owner: KIT-OPS-5. Fleet time: under 0.5 percent (6 gen stages), plus its share of (b).

### (f) Repeat on a cause never fixed, at gen

- Count (V): 9 gen failures on 4 items: s81 col_h9_r0_p1__t1__pv697f40c9 "OT_MACRO_MOVES overlap" 4 times (BLOCKED-REPEAT at
  3, then REPEAT-STOP RELEASE `inputs:tools` and the same failure again); KV kv3_hgi_v6, v7, kv3_pv_v1n "collector_tree differs
  from captured bound reset identity" 5 times. 6 S81 svc rows failed UNCLASSIFIED "no error line (progress text only)".
- Root cause: a tools change releases a repeat stop although the failure is in the plan input (rt moved 8 times 03:25-03:47).
- Structural fix (P): a PLAN or die-tool-refusal key at gen is released only by a changed plan block, bind or overlay.
- Owner: FLOW-HEALTH-1. Fleet time: under 0.1 percent (gen is minutes); it costs queue slots and attempt numbers.

### (g) Disk and admission

- Measured (V): scratch free epyc9 158 GB, intel1 161 GB, epyc2 217 GB, epyc8 396 GB, epyc10 596 GB, localhost 640 GB, epyc7
  855 GB. epyc9 lost 269 GB in 2 h. Admits: epyc2 0, epyc7 0 (5 waiters, 228 GB, oldest 0.8 h), intel1 14, epyc10 20,
  localhost 29, epyc8 58, epyc9 65 GB. No admission or disk refusal line in the window. 5 STOP-SURVIVOR checks on epyc7
  timed out (rc 124; load 124 on 96 cores, 403 threads granted).
- Root cause (I): epyc9 reclaim is refused while one container mounts a parent of many kits (7 deferrals); intel1 has a
  top writer not yet named (R, FLEET-WATCH-R4 scan).
- Structural fix (P): as 0200 (e); plus the wave stops choosing a host as gen target below 250 GB free, which Codex set by
  hand for epyc9 (coord dc77157231e).
- Owner: CLEAN-ALL-1115. Fleet time: none yet. epyc9 and intel1 reach the floor first.

### (h) Stale state, skew, hub hygiene

- STALE 106 (V): HBM 104 (parked, still no parked flag), KV 2 (qkd_pv_fin_s8_pin CANCELLED 18.3 h, unowned; kv3_io_cor_v1
  FAIL route INFRA 6.1 h, not retried), S81 1 (iqf__t1 ROUTE-HELD 10.3 h).
- Skew (V): TOOLS-LAG s81 unmeasured (`j5tree`); KV 562 commits behind, QC 154, HEAD 100, all missing r708; HEAD 9 of 18,853
  modules differ from pin (warn).
- Hub (V): HUB-SYNC-FAILED since 02:30, a local edit of lanes/posts/LOCKUP-STATION-R3.md in the hub checkout (a lane wrote
  its post file directly instead of bin/post.sh); 4 alerts. ADOPT-GUARD hbm alert 24 times in 2 h for a parked die.
- Tick (V): autopilot tick 230-719 s, wave step 140-460 s (plan_dies 243 s and bind_preflight 240 s in one tick).
- Structural fix (P): die config pin must be a sha (bind refuses a name); `parked: true` on a die silences STALE, TOOLS-LAG
  and ADOPT-GUARD for it; post files are written only by post.sh (hub pre-commit check on author path).
- Owner: MERGE-QUEUE-1 (pins, r708 re-pin with the die owners), FLOW-HEALTH-1 (parked flag, hub check). Fleet time: none.

## Do now (ordered)

1. FLEET-WATCH-R4: class (b), launch guard on a live attempt and reap keeps the attempt with progress. Evidence above.
2. KIT-OPS-5: `restage_min_wait_s` back to 1800 via kit_wave_edit; it feeds (b).
3. FLOW-HEALTH-1: fail key from the first ERROR line of run_route.log; cap per key; PLAN keys at gen not released by tools.
4. FLOW-GRT-RESID: drt-nopath after hours of route holds for the die owner; decide coll_ftc attempt 6 before it reaches route.
5. CLEAN-ALL-1115: epyc9 and intel1 below 165 GB; name the blocking container.
6. MERGE-QUEUE-1: s81 pin as a sha; r708 re-pin for KV, QC, HEAD at their next bind.
