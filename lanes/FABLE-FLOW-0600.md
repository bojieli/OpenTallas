# FABLE-FLOW-0600: procedural / flow review, window 11-22 03:50 to 05:55 PST

Lane FABLE-FLOW (Fable 5.2). Read-only review of process and tooling. Nothing cancelled, signalled, launched, deleted or
edited except this file and one RESULT post. Previous: lanes/FABLE-FLOW-0350.md (02:35 to 03:50).
Sources: autopilot/log.txt (1,385 lines from 03:50), journal of autopilot.service, lanes/FLOW-HEALTH.tsv (05:08),
`failure_breakdown.py` (05:44), `ot-run --status` (05:46), hub signals.log, 443 post lines from 03:50 (94 DIED, 133 DONE),
autopilot/kit_wave.json, `ps` / loadavg / df on all 7 hosts (05:50), rt/current (2bc14507b4d).
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Not done: no kit or bind log opened on a build host; signals logs of the 6 other hosts not read; only 4 of the 18
double-launched items were checked unit by unit; incident (g) "ssh 900 s" and (j) R8_STALE have no line in this window's
log or posts (taken from COORD; older instances cited). "Share" = estimate (I) against 624 gen cores x 2 h = about
1,250 core-hours, unless marked. At-risk figures are not losses yet.

## Headline

1. **Count: signed any plan 550 / current plan 440** (V 05:44); was 549 / 439 at 03:44. One sign-off in 2 h (kv3_io_cor).
2. **All 227 wave launches in the window are S81 J7** (V): 21 at 04:40, 205 at 05:10, 1 later. QC, KV, HEAD: 0.
3. **194 of the 205 rows launched at 05:10 were rows their die owner meant to hold** (R, S81-J6-ASSEMBLY-R5; V: leaf 75,
   col 72, serdes 8, svc 16 in the LAUNCH lines). 8 serdes cancelled 05:15 (functional reset bug); 186 run on.
4. **The fleet went from 70 to 80 % busy to 133 to 145 %** (V): load 439 -> 907 on 624 cores, threads committed
   1,516 -> 2,618 (420 %). At 05:50: epyc9 219/96, epyc2 198/128, epyc10 162/96, epyc8 150/96, intel1 141/112.
5. **NEW: 18 items are launched twice** (V): the tick killed at 04:42 had already launched 21 units and saved no state;
   the 05:10 tick launched 18 of them again. 3 of 4 sampled have both units active now (e.g. col_h10_r1__t1__cld01bb4ae
   units -51262 and -53017). Same item, same plan a6771d121e95, two kits.
6. **No tick completed from 04:24:49 to 05:11:46 (47 min)** (V): journal `start operation timed out` at 04:42:08 and
   04:59:33. 164 of 624 cores were idle at 04:24.
7. **A QC plan_gate_pre has run 65 min on one core and is still running** (V, epyc8: 3,890 s elapsed, 3,664 s CPU; a
   second at 814 s; 3 more on epyc10 at 334 s). QC-PLAN-R13 05:44: "no candidate was bind-clean by 05:40".
8. **HOLD-AUDIT printed HELD-BUT-LAUNCHED=0 in all 8 ticks, including the leak tick** (V). The audit did not see it.

## What FABLE-FLOW-0350 asked for: state now

| 0350 item | State at 05:55 |
|---|---|
| S1 bad byte | FIXED (V): byte cc34fb238d; reader tolerant c9b8d5f226ca; post.sh / coord-commit refuse invalid UTF-8 (R). Last `hold recompile skipped` 04:05, LOOP-GAPS written again 05:39 |
| R1 first STRUCTURAL verdict blocks | LANDED and seen working (V): ec9c345795c; 05:20 serdes__t16 BLOCKED-PLAN "(first failure)" |
| U1 flagged holds -> OWNERS rows | LANDED (R, af2435fb9ab). Flagged keys 59 -> 5 (V). But S81 holds 344 -> 2 is the leak of class H1, not a release |
| B1 re-check live binds | LANDED as bind_doom (aad13eaaab6), caused incident E1, guarded ba20f11e2d8; its 900 s check times out on a full QC plan (R) |
| T1 min_rt on plan-job bind | LANDED (R, c9b8d5f226ca). Hub still runs 20+ rt versions (V) |
| P1 run-item in a unit | LANDED (R, c9b8d5f226ca); live drivers not restarted |
| A1 hub disk | No floor refusal in the window (V: 1 DISK line in signals.log); hub 608 GB. DISK-RATE state 1 on 4 hosts (5.3 to 5.8 h to floor) |
| D1 death classes | NOT landed (V): NO-PATTERN 37 of 94 DIED (39 %; was 40 %) |
| N1 repeating lines | NOT fixed (V): ITEM-SYNC phy_serdes_b rc=2 every tick, hbm bind preflight UNKNOWN (missing die_plan.json) every tick, ADOPT-GUARD 30, s81_cl canary NO-BASELINE on every run |

## Classes, ranked by fleet hours

### H1. A hold that the tool accepts and then ignores. Incident (b). Largest.
- Count (R/V): 194 rows launched against 12 hold records; 8 cancelled after 5 min; 186 running; 149 not yet launched
  were re-held as hold_items (V: s81 hold_items 151). Trend: new; first event applied with records only.
- Root cause: `hold_records.compile_holds` skips every die with stops off (r703: all but hbm), so a record on S81 is a
  no-op, yet kit_wave_edit accepts it, and the apply receipt and HOLD-AUDIT show nothing wrong. The apply step then
  dropped the 342 hold_items that did block. Two hold mechanisms, one of them silent.
- Structural fix (P): no new hold. (1) kit_wave_edit refuses a hold record on a die where records do not block, or
  writes the same keys as hold_items in the same edit. (2) Any edit that removes hold keys prints "N rows become
  launchable" from a dry select and needs `--expect-launch N`. (3) HOLD-AUDIT counts launched rows that match any
  record, effective or not.
- Owner: WAVE-FLOW-R2. Share (I): at risk about 1,100 committed threads (the growth 1,516 -> 2,618), 40 % of the fleet
  from 05:10 until these kits end. Realised loss = the kits that fail on the reason they were held for (col tap
  density, leaf, svc); first fails seen: 4x col_h9_r0_p1 OT_MACRO_MOVES overlap, 1 col_h9_r1 station sites, 1 leaf t31.

### W1. One slow probe kills the tick; a killed tick forgets what it launched. Incident (a).
- Count (V): 2 ticks killed (04:42, 04:59), 47 min without a saved state, all dies. 18 double launches. Ticks that do
  finish take 307 to 687 s of a 900 s limit (bind_preflight 516 s + plan_dies 411 s at 04:15); state file 52.7 MB.
  PROGRESS-WATCH raised TICK-DEAD at 04:54, 30 min in; the fix came from a die lane at 05:00.
- Root cause: the tick is one all-or-nothing transaction: synchronous ssh probes of 395 items inside it, state written
  only at the end, launches made before the write.
- Structural fix (P): (1) write a launch record before each systemd-run and read it at tick start, so a killed tick
  cannot launch twice; (2) save state after each phase; (3) probes run in a detached unit and the tick reads their
  cache (as SRC-SYNC already does); (4) a phase whose last duration exceeds the time left is skipped this tick;
  (5) TICK-KILLED twice in the same phase alerts COORD at once. S81 bind_preflight goes back on after (3).
- Now: WAVE-FLOW-R2 to list the 18 duplicates and stop one copy of each (same plan twice signs nothing more).
- Owner: FLOW-OPS-R2 (tick), WAVE-FLOW-R2 (duplicates). Share (I): 164 idle cores x 0.78 h = 128 core-hours, about
  10 % of the window; plus 18 duplicate kits, about 140 threads (5 %) for as long as both copies run.

### F1. CPU oversubscription: admission counts memory, not cores. Incident (f).
- Count (V): 5 of 6 gen hosts above their core count at 05:50, epyc9 at 2.3x; `ot-run --status` still admits on all
  (epyc2 66 GB at 568 threads / 128 cores). LOAD_CAP_FACTOR is set on epyc7 only (V, HOST-REPORT), and epyc7 is the one
  host at 1.0x. Tree copy on epyc8 680 MB in 8 min, lane moved (R). Trend: up, caused by H1.
- Root cause: one tick may launch any number of rows; memory admission passes them because early stages are small.
  The owner rule "representatives first, then siblings" is not in the launch order.
- Structural fix (P): launch order of a new event = one representative per family first, siblings in later ticks as
  load allows (existing wave_balance); the load factor that epyc7 has, on every gen host, so excess rows wait in the
  ot-run queue instead of time-slicing. The second part reads as a cap: COORD to rule.
- Owner: FLOW-FLEET-R2. Share (I): 10 to 20 % throughput loss while load is above 1.3x, and every single-thread gate
  (bind, plan_gate_pre, copies) stretches by the load ratio on epyc9 / epyc2.

### K1. A plan cut loses rows without telling anyone. Incidents (k) and (i).
- Count (V/R): 2 in the window. (k) KV-PLAN-R6 cut the RESET-RELAY-GEN relay rows for hub_Eo / hub_Wo from D27d2
  ("relay_depth matched no sink"); D27d3 shipped without them; hub_Eo proof kit post-hook CTS setup -754.69 ps, reset
  path about 2,200 um through 33 buffers (R, OPUS-FIX-KV-HUB-R6 05:39: "the known -747 path"). (i) d28/rows/ holds 8
  ROWS_*.py, rows.json lists 6 owners; FIX-SYNC-KVHEAD and KV-RINGMAC-R1 rows missing (R, 04:56). Also FAM-KV-HUBC-SYSC
  kv3_sys_c D27d3 kit failed at -417.86 ps with 285 NEED-STATION groups "row=none".
- Root cause: the cut is a hand-run script per die; a row that does not apply is dropped inside it; the manifest is
  hand-listed; nothing links a row to the problem it was written for.
- Structural fix (P): one cut ledger written by the cut tool: every row file found in the rows directory (glob, not a
  list) -> APPLIED / DROPPED with the reason, and one DROPPED post to the row's owner lane per dropped row. A row
  carries a problem key (type + path or metric); a dropped row whose key is still open in PRECHECK becomes an OWNERS
  row. A file in the directory that the manifest does not name is reported, never skipped.
- Owner: new Sonnet lane (cut ledger in tools/die_plan, used by KV-PLAN-R6, QC-PLAN-R13, S81-J6-ASSEMBLY-R5).
  Share (I): 1 to 2 % of threads (kits built on a base with a known open path); calendar: one plan event (24 h) per
  lost row on hub_Eo, hub_Wo and the 2 D28 row sets.

### G1. A 1 h single-core check in front of every QC bind chain. Incident (d).
- Count (V): 5 plan_gate_pre --tree runs live on full QC plans; longest 65 min and running, 94 % CPU-bound on one core
  (not I/O, R). bind_doom's 900 s limit cannot finish on QC (R). RESETPUB's die-wide reset solve did not finish in
  3,400 s and was replaced by a 4 s identity check (R, 2bc14507b4d). Bind units dead in the window: 74 thread-hours
  (V: QC-PLAN-R13 4 x 2.3 h cancelled + 1 x 4.2 h rc 1; was 32).
- Root cause: a whole-die solve runs for a delta of a few types, once per chain, with no shared result, and chains wait
  on it although bind does not need it.
- Structural fix (P): profile the TAPNAME density solve on the 1,921-crossing plan; cache the solved base by (base
  plan sha, tree manifest) so chains on one base share it; check only types changed against `--baseline-plan`; run
  it beside bind, not before it. As for RESETPUB: any check over 60 s becomes an identity check plus an opt-in solve.
- Owner: new Sonnet lane (profile + cache), FLOW-OPS-R2 (chain order). Share (I): under 1 % of cores; about 1 h of
  calendar on every QC chain; QC had 0 wave launches in the window and took the fallback pick at the 06:00 cut.

### C1. Private-kit goal words that mean different things per code path. Incident (c).
- Count (V): 18 DIED class SETUP, 12 of them rc 10 (FAIL_PREFLOOR on stage resume): FAM-S81-SLICE-R6 6, COL-H9R0-R4 2,
  HEAD-LEP0N, COLROM-R6, KV-HUB-R6, S81-BKSEL-R7 1 each. Fixed on main 36d0a6df8f6 at 05:26; one more rc 10 at 05:40
  (S81-BKSEL-R7) after the fix, before rt/current followed (05:39). The COORD 02:52 ruling said `--goal finish`.
- Root cause: three goal vocabularies (private-spec, chain, run_kit.sh resume) with no shared table; the brief text was
  typed by hand; lanes launch run-item from their own rt (20+ versions on the hub).
- Structural fix (P): one goal table imported by all three, with a test that every goal reaches sign-off or names its
  stop; run-item on a private spec re-executes from rt/current; brief text for commands is pasted from `--help`.
- Owner: FLOW-FLEET-R2. Share (I): 1 to 2 %: about 12 kits x 1 h of calendar each, threads small (stages died in 16 s
  to 12 min).

### E1. A test that starts real fleet work. Incident (e).
- Count (R): 64 sweeps, 189 remote scans, about 10 min, epyc9 load 197. Guarded ba20f11e2d8. One instance.
- Root cause: fleet side effects (ssh, systemd-run) are reachable from code under pytest; the guard is per feature.
- Structural fix (P): the test harness sets OT_UNDER_TEST=1 and the shared ssh / systemd-run / ot-run helpers refuse
  under it unless a test names a fake. One guard for every future feature.
- Owner: FLOW-OPS-R2. Share: under 1 %.

### X1. False or missing signals. Incidents (g), (h), (j).
- Count (V): a hand-made waiter grepped a NUL-separated cmdline and posted a kit as ended at 04:07 (corrected 04:49);
  ot-push-main rc 1 after 910 s with no log (FABLE-FIX-KV-PV-SINKSPREAD); 10 signed S81 provider cores still show as
  "no kit-wave row" at 05:44 (62/72) after PROVENANCE.json was written at 04:58; HUB-SYNC-FAILED from 04:26 to at least
  05:34 (8 alerts; hub checkout edited outside coord-commit: OWNERS-SWEEP.tsv, then posts/FAM-S81-COL-H9R0-R4.md,
  still dirty 05:50); DIED posts mix UTC and PST end times. R8_STALE: 0 in the window; 2 earlier today (00:20 QC CB,
  02:22 KV pc_v3, 30 bundles).
- Root cause: waiters and launches written per lane; counters depend on a file only some paths write; station-row
  chains call bind without the refresh that QC bind_v2.sh has.
- Structural fix (P): launches detach through ot-run so no ssh session limit applies, and ot-wait --durable is the only
  waiter (already the rule; make post.sh DONE / PROVENANCE for a kit read result.json). The counter lists signed cores
  without PROVENANCE as UNCOUNTED with the missing file. `ot-build --goal bind` runs r8_refresh and rebinds once
  on R8_STALE. A dirty hub file names the writing process in the alert.
- Owner: FLOW-FLEET-R2 (waiters, counter), FLOW-OPS-R2 (r8 loop). Share: 0 direct; the headline
  count is short by up to 10 cores.

### D1 / N1. Unclassified deaths and repeating lines: unchanged from 0350 (see table). Owner FLOW-FLEET-R2 / FLOW-OPS-R2.

## Requests to COORD (ranked)

1. W1 now: WAVE-FLOW-R2 lists the 18 double-launched S81 items and stops one copy of each.
2. H1: kit_wave_edit refuses a no-op hold record; removing hold keys needs `--expect-launch N`. S81-J6-ASSEMBLY-R5 to
   post per class which of the 186 leaked rows can sign on J7, so the rest follow the measured stop rule early.
3. W1: launch record before systemd-run, state per phase, probes detached (FLOW-OPS-R2).
4. F1: rule on the load factor for all gen hosts; representatives-first launch order for a new event.
5. K1: cut ledger with DROPPED posts (new Sonnet lane). G1: profile and cache the TAPNAME solve (new Sonnet lane).
6. C1, E1, X1, D1, N1 as above.
