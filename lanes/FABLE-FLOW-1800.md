# FABLE-FLOW-1800: procedural / flow review, window 11-20 15:45 to 17:50 PST

Lane FABLE-FLOW-1800 (Fable 5.2). Read-only review, flow only. Previous: lanes/FABLE-FLOW-1600.md.
Sources: autopilot/log.txt (1,613 lines from 15:45), ot-run --status (17:47), /var/tmp/ot-heavy state and process
tables on the 6 build hosts (17:48), tools/failure_breakdown.py (17:46, read-only), intel2 ot-run signals.log and
/tmp/push-*.log, autopilot/kit_wave.json, lane posts and handoffs (FLEET-WATCH-1630, WAITER-STD-1600, FLOW-NOADV-R3),
lanes/FABLE-CLOSURE-STRATEGY.md (17:35).
Marking: **V** = I read or measured it this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.

## Headline

1. **AUTOSTAGE has not moved a waiter that I can find (V).** epyc8 holds 32 waiters asking 1,916 GB, the same count
   as at 15:45 (31 to 32, 1,990 GB). Median wait 4.3 h, longest 17.9 h, 24 older than 1 h. The intel2 signals log has
   no AUTOSTAGE line and its last SPILL-HANDOFF is dated 11-14. Cause: a waiter keeps the ot-run code it started with.
   23 of the 32 started before the runtime that carries AUTOSTAGE was synced. See class 1.
2. **The fleet-wide queue did fall: 183 waiters (15:50) to 42 (17:47) (V).** That is the autopilot RESTAGE (45 moves
   in the window, to 4 hosts, not only epyc7) and cancelled rows, not ot-run. Only epyc8 is left behind.
3. **Launches (V, KIT-WAVE LAUNCH lines): hour 16 = 93, hour 17 = 41 in 43 min (57 per hour pace).** I do not
   reproduce 97 per hour for hour 17; 93 is hour 16, and 44 of those are one burst at 16:30 to 16:39.
4. **The J5 failure is one structural fault, not three accidents (V + R):** an event source tree is forked from the
   previous event's tree, so a fix that lands on main never arrives unless a person carries it. S81 src is
   `src_s81_pin_3c913dbdfb23_d8j5_1117_work` (cut 11-17), its tools pin is the word `j5tree`. See class 2 for the fix.
5. Start canary, ot-wait and status files, the auto-visual reviewer and the cancel marks all work as posted (V).

## What 16:00 asked for and what happened

| 16:00 item | state at 17:50 |
|---|---|
| Auto-visual reviewer not on main | landed 16:32 (push-rr1300c PUSHED after one more failed try 16:04); 8 runs since 16:41, 8 accepts; WAIT-VISUAL 64 -> 46 |
| epyc7 admits but cannot start | start canary on all 6 hosts, green, 0.7 to 8.7 s (epyc10 slowest) |
| J5 tree on epyc7, s81 gen_hosts | done: s81, kvsys, qc and s81_head gen_hosts all include epyc7 |
| ot-run moves waiters with inputs | landed (AUTOSTAGE), no effect seen: class 1 |
| Standard waiter | landed 2c5b84faf6; ot-status files on 5 of 6 build hosts; 68 shells killed. 86 pgrep shells remain on the build hosts, 75 over 24 h (the "chained work" set, left on purpose) |
| HUNG-WATCH cancels admission waiters | 1 cancel (15:53, serdes t16, containers none), was 5; 3 correct no-cancel posts |
| Reason extractor, CLASS post | not seen landed; class 5 |
| Pin manifest at pin time | not landed: kvsys and s81_head still UNMEASURED, s81 lag unmeasured; class 2 |
| Push timeout default | not checked |

## Classes

### 1. Waiters that cannot move (epyc8)

- Count, trend (V): epyc8 32 waiters / 1,916 GB at 17:48 (15:45: 31 to 32 / 1,990 GB). Flat for 2 h. Other hosts:
  epyc7 7 / 272 GB (median 28 min), epyc9 3 / 72 GB, epyc2, intel1 and epyc10 none. epyc8 admitted 3 to 8 requests
  per hour since 12:00; the other hosts 18 to 262. epyc8 load 335 to 367 on 96 cores for the whole window, 60 GB
  available, status prints "peak 0".
- What the 32 are (V): 16 kit-wave, 16 lane.
  - 9 route kits of 96 GB from s81-geom-opus-d8g (D8i plan), 17.9 h. No host admits 96 GB now, so these wait for
    memory anywhere; they are old-plan kits and stay.
  - 13 lane or wave jobs of 10 to 40 GB, 1.5 to 16 h: 3 count.sh of FABLE-FIX-S81-SVC-R2 (40 GB, 4.3 h), 1 sts_dump of
    cbc-all-0200 (32 GB, 16 h), 6 kit-gen lint (10 GB, 0.8 to 3.2 h), 3 geom_check (24 GB, 2 to 2.9 h).
    epyc10 admits 85 GB, epyc2 45 GB, intel1 28 GB: every one of these fits somewhere now.
  - 3 with no ot-run above them, 7.0 h: `hop.tcl` of S81-DIE-R4 j6_lockup (24 GB, started on epyc8 with docker -v), and
    2 LEC units whose whole command is `echo LEC_PREPLACE_DROPPED R-MINIMAL`. Two echo commands have waited 7 h for
    24 GB each.
  - 7 route kits of 72 to 126 GB from event b05c98f7919, 3 to 30 min: normal.
- Root cause (V for the first two, I for the third):
  1. A waiter is a running Python process. It never reloads. 23 of the 32 started before 16:29 and run the ot-run
     without AUTOSTAGE. A fix to the waiter reaches only jobs submitted after it.
  2. AUTOSTAGE and the 300 s requeue live in the ot-run client. A job started with ot-heavy or docker on the host
     has no client and cannot move.
  3. The 6 lint and 3 geom waiters started after 16:29 did not move either. I did not find why; the client prints
     AUTOSTAGE only to its own stderr, so there is no fleet record of a refusal or a move.
- Structural fix (P):
  - ot-run: while WAITING (never after start), when `rt/current` changes the client re-execs itself with the same
    arguments and its original start time. Every waiter then runs the current code within one requeue period.
  - ot-run writes one line per decision to signals.log: AUTOSTAGE moved / refused (reason) / REQUEUE no host. Without
    it, "is it working" needs a process walk on six hosts.
  - ot-run --status prints the oldest waiter age per host. A host with waiters older than 1 h while another host
    admits their size is one hub post per hour (post only).
  - A unit that only records a result (the LEC drop marker) asks for no memory: `--mem 0` path that skips admission.
- Do now, by the lanes that own the jobs (no code needed): S81-DIE-R4 re-submit `hop.tcl` on epyc10;
  FABLE-FIX-S81-SVC-R2 re-submit the 3 count.sh; kit-wave lint and geom rows re-submit on the next RESTAGE.
- Owner: FLEET-WATCH-1630.
- Fleet time: compute 0 (no idle thread on any host). Memory: 158 GB admit idle of about 6 TB, 2.6 percent. Lane
  time is the loss: 7 h on a J6 lockup measurement, 4.3 h on three svc counts, 16 h on one dump.

### 2. Event built from an old tree: fixes on main missing, regressions not compared (J5)

- Count, trend: 1 event (J5), 32 item patterns stopped at 17:26 as unable to sign (R, S81-DIE-R4): 29 types with a
  landing-monitor pin 300 to 2,904 um from its monitor, plus seqhost and the lepe / lepw LP families that lack a fix
  proven on main (hwin 8e20268b5d83 of 11-19; the `OT_S81SL_LEP_RIP1` define) (R, FABLE-CLOSURE-1730, its V).
  Tools lag (V, 17:40): s81_head 887 commits (missing r698 r708), qwen_kvsys 409 (r708), qwen_compute 1,894
  (181 named rules), s81 unmeasured (`bad revision 'j5tree..main'`). TOOL-SKEW: kvsys and s81_head UNMEASURED (pin
  manifest on no host), s81 489 of 18,020 modules differ from the pin, qc 485 of 17,987. Unchanged since 14:00.
- Root cause (V + I). Three separate pins per die (source tree, tools_sha, runtime) and none is tied to main:
  1. The source tree of an event is a copy of the previous event's tree plus the event's edits. The name says it:
     pin 3c913dbdfb23, work tree cut 11-17. A fix pushed to main on 11-19 is in no step of that path.
  2. A pin may be a label. `tools_sha = j5tree` is accepted, so the lag check has nothing to count from.
  3. TOOLS-LAG and TOOL-SKEW are printed 12 times an hour as warnings to nobody. 60 TOOLS-LAG lines in this window,
     no owner line, no action.
  4. Nothing compares an event with the event before it. The monitor pins moved by up to 2,900 um between
     3fa87b84b18 and J5 and the first reader was a timing report after place.
- Structural fix (P). Two tools, both run on the sealed event before apply, both without a build.
  - **ADOPT-DIFF** (`tools/plan/event_adopt_diff.py <die> <event tree>`). For every file under the die's RTL, die_plan
    and tool closure it compares three versions: the pin, the event tree, main.
    - tree == pin and main differs: **LAG**. The event did not touch the file and main moved. Carried automatically
      (the file is taken from main); the result is listed in the apply receipt.
    - tree differs from pin and main differs from pin: **BOTH**. Listed with the main commits; the die owner merges or
      names a reason per file in the receipt.
    - Named fixes: ot-push-main records a `Proven-For: <die>/<family>` trailer and any define or recipe key the fix
      needs into `lanes/PROVEN-FIXES.tsv`. ADOPT-DIFF checks each row of the die: commit is an ancestor of the event's
      tools and source, and the define is in the generated `config.mk` of one kit of that family. This is the row
      that would have caught RIP1 (branch present in the RTL, define absent) and hwin.
    - A pin must resolve with `git rev-parse` and its runtime manifest is written when the pin is made;
      kit_wave_edit refuses a label. Then TOOLS-LAG and TOOL-SKEW can always be measured.
    - End state to aim for: event tree = main at seal time + the event's own delta. Then lag is zero by construction
      and ADOPT-DIFF prints only the delta.
  - **EVENT-CENSUS** (`tools/plan/event_census.py <die> <previous bind> <new bind>`), in the PRECHECK-1119 checker.
    Per type, from the two binds and one generated kit each: infrastructure pin to consumer seat distance (the
    `monc.py` of FABLE-CLOSURE-1730), longest hop and count of hops over 300 um, relay count, reset sink depth,
    unregistered memory reads, clock taps, pin count and the largest pin move, defines in `config.mk`.
    Output `EVENT-CENSUS.tsv` with one REGRESS row per type and metric that got worse than the previous event past a
    stated step (pin distance over 300 um, hop over 300 um, a define lost, an unregistered read gained).
  - Use of the result, without a new event gate: the event applies as today. A type with a REGRESS row is not
    launched by the wave until the row is cleared or the die owner names it as intended. That is the 17:26 stop,
    made at apply time instead of 4.5 h later. Functional errors block as before.
  - TOOLS-LAG becomes one post per die per change, to the die owner, with the list of missing proven fixes; not a
    line per tick.
- Owner: new lane (ADOPT-CENSUS-1800) for both tools; PRECHECK-1119 hosts the census; FLOW-NOADV-R3 for the pin
  form and the manifest at pin time (asked at 14:00 and 16:00, still open).
- Fleet time (I, not measured): J5 was applied about 13:00. S81 took 123 of 134 launches in this window and holds
  154 running rows; 32 patterns of 394 types were stopped. If the stopped types ran in proportion, that is roughly a
  tenth of S81 compute for 4.5 h, about 5 to 8 percent of the fleet, plus the builds still running on them (admitted
  jobs were not cancelled). The larger cost is the event: J6 has to repeat J5 for these types.

### 3. Runtime refresh breaks a plan gate in flight

- Count, trend (V): rt/current moved at least 5 times in the window (81c8692c1cdf 16:3x, bbcc7f022a8e, 65f3f85d7c5f
  17:09, 3553de9af815 17:26, b8ab33d192d9 17:46). 1 loss: KV D26 R3b exited 1 at 16:5x, "only the runtime pin check
  failed" (R, KV-PLAN-R2); re-run as R3c.
- Root cause: the gate compares its pin with `current`. Each landing moves `current`. More lanes landing means more
  gates lost; 16:00 to 18:00 was the busiest landing period of the day.
- Structural fix (P): a gate opens `rt/<sha>` at start and uses that directory to the end; the check becomes "my
  directory is whole (manifest)", not "current equals my pin". The directories are already kept per sha.
- Owner: FLOW-NOADV-R3. Fleet time: one plan gate run (compose + G0), on the KV event path.

### 4. Kill reason recorded two ways

- Count (V): 2 rows (qc slw_sc_v1 17:05, sle_stm_v1 17:17). CLASSIFY says "CRASH (infra-stopped): exit 143, no OOM
  line: stopped from outside"; two minutes later REPEAT-STOP says "OOM kill; the resubmit runs with place memory
  x1.5". Last window: 2 lines of the same kind.
- Root cause: two code paths read the same exit; one assumes OOM for any 143. If the stop was a cancel or a guard
  kill, the resubmit asks 1.5 x memory for nothing, on hosts that admit 0 GB.
- Structural fix (P): one function gives the kill cause (the CANCELLED mark of 8be8f420531, the earlyoom journal line,
  the guard log); memory is raised only on a recorded OOM or guard kill.
- Owner: FLEET-WATCH-1630. Fleet time: under 0.5 percent; it makes class 1 worse by raising requests.

### 5. Unchanged retries and one class counted per type

- Count, trend (V): FAIL lines 2 (15:45 to 15:59), 8 (hour 16), 1 (hour 17 to :43). Previous window 14, 10, 8.
  - qc sle_st_a_v1, two forms, the same kit_topology overlap (rs_s0 / rs_s1, 20 overlaps) at 16:11, 16:41 and 16:58:
    6 of the 11 FAIL lines, class UNCLASSIFIED. None after 16:58 (the overlap PLAN class, ccc542c1af, is in).
  - s81 serdes t3 and t4: DPL-0033 at detail_place, 16:27 and 16:41, two types of one family, counted alone.
  - REPEAT-STOP: 1 LAUNCH-HELD (hd_host_e, 3 identical), 6 releases on changed input, 15 SKIP-SAME-INPUT.
- Root cause and fix: as 16:00 class 6 (reason extractor, one CLASS post at 3 types of a family). Not landed.
- Owner: FLOW-NOADV-R3. Fleet time: under 0.5 percent (all fail at kit_topology or place).

### 6. Jobs with a frozen log for 6 h

- Count (V): 3 HUNG-WATCH posts (s81 svc_lo_dsdv_svc_rs t4 and t2, kv_leaf t2): log frozen 360 to 366 min, CPU busy,
  not cancelled. 99 REAP-DEAD SILENT report lines in the window, about 8 per tick, all "reported only".
- This is the watchdog working as designed. The open part is a decision: each of these has run over 3 h; kv_leaf t2
  is in the J5 stop list (monitor pin 1,610 um). The owner rule (cancel over 3 h when measured unable to sign) applies
  to it once S81-DIE-R4 records the evidence. svc_lo t2 / t4 need a stage read first.
- Owner: S81-DIE-R4. Fleet time: 3 jobs of 23 to 28 processes, about 1 percent.

### 7. STALE and non-design classes (failure_breakdown 17:46)

- Count line: signed any plan 474, current plan 409 (both unchanged since 15:46). Deferred re-sign 6, retired-plan 59.
- STALE 104 current-event (15:46: 105): HBM 104 minus 2 not counted = parked (lint advisory 42, cancelled superseded
  about 50, no row 7, route-held since 11-13 5); QC 1 (sle_hc1__cl7d360508, cancelled 09:37, KIT-WAVE-1); KV 1 (core
  qkd_pv_fin_s8_pin, cancelled 09:28, still unowned, second review in a row).
- Non-design rows: KV "other flow error" 4, PDN-0006 2, bind stale 1 (kv3_pv_v8); S81 cancelled superseded 2,
  CLAND ring band 1; QC cancelled superseded 2, place error 1. hub_C needs a re-freeze, not a relaunch (R, KV-PLAN-R2).
- ALERT ADOPT-GUARD PLAN_MISSING hbm on epyc2 prints every tick (12 per hour) for a parked die.
- Owner: KV-PLAN-R2 for the KV rows and the unowned core. No fleet time.

### 8. Disk, admission, source completeness

- Disk (V): no refusal in the window. Used: intel1 scratch2 94 percent (216 GB free), epyc8 93, epyc9 91, epyc10 89,
  epyc2 root 88, epyc7 82. intel1 and epyc8 are up 1 to 2 points on 15:50.
- Admission (V): no "NOT RUN" and no lock timeout in the window.
- SRC-INCOMPLETE (V): 6 lines. epyc7 at 15:55 and all 5 other S81 hosts at 16:30 lacked memory macro views in the
  post-bind tree; SRC-SYNC copied 104 files per host from intel1 in the same tick. Self-heal worked; the cause (a
  post-bind tree published without its macro views) is the same family as class 2: the tree is not checked whole
  against a manifest when it is made.
- Owner: FLEET-WATCH-1630 (disk), ADOPT-CENSUS-1800 (tree manifest). Fleet time: one tick of S81 launches.

## Fleet time, summed

| Class | Share |
|---|---|
| 2. J5 types that cannot sign | about 5 to 8 percent for 4.5 h (I) |
| 1. Admit idle while epyc8 waits | 2.6 percent of memory, compute 0 |
| 6. Frozen-log jobs | about 1 percent |
| 4 + 5. Kill reason, unchanged retries | under 1 percent |
| 3, 7, 8 | lane time only |

## Do now (ordered)

1. New lane ADOPT-CENSUS-1800: ADOPT-DIFF and EVENT-CENSUS; run both by hand on the J6 private bind before its apply.
2. FLOW-NOADV-R3: pins are real shas with a manifest (s81 `j5tree`, kvsys, s81_head); gate uses its own `rt/<sha>`.
3. FLEET-WATCH-1630: waiter re-exec on runtime change, AUTOSTAGE and REQUEUE lines in signals.log, oldest waiter
   age in --status, one kill-cause function.
4. S81-DIE-R4, FABLE-FIX-S81-SVC-R2: re-submit the 4 stuck lane jobs from epyc8 on epyc10 today.
5. FLOW-NOADV-R3: reason extractor and CLASS post (third review asking).

Not checked: why the 9 post-16:29 lint and geom waiters on epyc8 did not requeue; whether any AUTOSTAGE message
went to a client's stderr; OOM kills in the earlyoom journal; the launch count of 97 per hour given to me; git
history (no git run in the owner checkouts), so the commit lag figures are the autopilot's; J5 pins and source
files themselves (FABLE-CLOSURE-1730 read them); push gate timing; localhost and intel2 waiter shells.
