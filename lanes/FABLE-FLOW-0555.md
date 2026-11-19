# FABLE-FLOW: flow and procedural review, 03:43 to 05:50 PST 11-19 (FABLE-FLOW-06xx, read-only)

Sources: autopilot/log.txt (4,648 lines in the window), kit_wave_state.json (05:44), failure_breakdown.py (05:44),
ot-run --status (05:46), /var/tmp/ot-oom-age/kills.log and /var/tmp/ot-heavy/admit.log on the 6 build hosts,
lanes/FLOW-HEALTH.tsv (05:08), posts of WAVE-PILOT-FIX, WAVE-TICK-1119, FLEET-OPS-R, S81-DIE-R3, KV-D23-COMPOSE,
FAIL-ROUTE-1115, DIE-LEVEL-CHECK-1119, and the last review FABLE-FLOW-0358.md.

Window totals (last window in brackets): LAUNCH 22 (69): QC 16, HEAD 6, S81 0 (37), KV 0 (2). FAIL 5 (48).
CANCEL-SUPERSEDED 6 (213). Guard kills 1 (85). REPEAT 8 (43). REPEAT-STOP 2 (14). SRC-INCOMPLETE 58 (24).
FLOW-HEALTH per hour, 00h to 05h: launches 90, 74, 37, 7, 7, 3. Passes at 01h 37, 03h 20, 04h 21, 05h 2 (partial).
Threads stay 91-98% used (idle 14-54 of 624) because lane jobs and old rows fill the hosts. The loss this window
is therefore wave rows that do not start, not idle hosts. Waste shares are estimates; none is measured exactly.

## Ranked by fleet time wasted

### A. S81 and KV have no launchable tree: bind not green. Largest, still rising. Estimate 20-30% of wave output.
- S81: BIND-STALE held rows 266 (03:47) -> 287 (05:34), 289 in the state at 05:44. S81 launches in 2 h: 0.
  State: s81 ENQUEUED 163, FAIL 230 (kit_rtl 104, place 51, gen 19), RUNNING 3. The die event keeps moving:
  D8g live, D8g2 not adopted, D8h G0 and bind running, D8i already queued (S81-DIE-R3 05:13). Each event needs its
  own bind, and no bind has gone green on the live tree since 02:28.
- KV: 0 launches. 48 SRC-INCOMPLETE lines (bind_report.json missing on epyc7/8/9/10), so KV has no gen host.
  KV-D23-COMPOSE 05:40: both strict binds are RED (D25c: 2 EMIT errors on hgi_v1 reset relays rst_rl_127 /
  rst_rl_120; D25d: the same 2 plus 30 R8_STALE). KV has no bind of record. 37 KV rows ENQUEUED on older events.
- Landed from 0358: the wave keeps a superseded row while its replacement is BIND-STALE (0017e104f9, in rt
  0ad8719029d8). It works: CANCEL-SUPERSEDED 213 -> 6, SUPERSEDED-KEEP 57, SWITCH-SUPERSEDE-KEEP 35.
  OLD-PLAN-FINISHES f67dc25e83 is on main but NOT an ancestor of rt 0ad8719029d8 (the newest rt named in the log);
  the SUPERSEDED-KEEP lines show the keep behaviour is active anyway. Bind-first publish_apply is on main; no
  S81 or KV event has completed through it yet (S81-DIE-R3 03:52: adopt-bind checks against the live plan, so it
  cannot be used before the D8g2 tree is live).
- Not landed: the adoption gate. A tree still becomes the die's tree before its bind is green, and new rows can
  only launch on that tree.
- Root cause: launch is tied to the newest tree, and the newest tree is published before its bind. Keeping the
  old rows stops the cancel loss but not the launch stop.
- Structural fix: the wave launches each ENQUEUED row on the newest tree whose bind preflight is green for that
  item (per item, not per die). A red or missing bind on the newest tree then costs nothing: rows keep launching
  on the last bound tree, and any-plan sign-off counts (OWNER 11-19). publish_apply refuses to switch the die's
  src unless bind_report.json exists on every gen host. For KV: a bind EMIT error on a renamed relay names the
  plan field that still holds the old name (clock.landing_raw_branches) and the event is refused at apply.
- Owner: WAVE-PILOT-FIX (per-item launch tree, apply refusal), S81-DIE-R3 and KV-D23-COMPOSE (binds).

### B. CPU placement: epyc8 and epyc9 run at 2 to 2.5x their threads while other hosts have room. Estimate 5-10%. New.
- ot-run --status 05:46: epyc8 load 244/96 (86 jobs, 773 threads asked), epyc9 194/96 (94 jobs, 879 threads),
  intel1 117/112, epyc7 104/96, epyc10 95/96, epyc2 131/128, localhost 40/112 with 106 GB admitted.
  UNDER-USE shows epyc8 133-241 and epyc9 196-259 in all 11 ticks.
- Root cause: admission is memory-only (correct, OWNER 11-14) and the host choice is "most free memory". Thread
  demand is not part of the choice, so small-memory jobs pile on two hosts.
- Structural fix: among hosts that admit the job's memory, ot-run picks the lowest load/threads ratio. This is
  an ordering, not a limit: nothing waits that would not wait today. The slowdown on epyc8/9 is UNMEASURED;
  compare one item's place wall time on epyc8 against epyc10 to size it.
- Owner: FLEET-OPS-R.

### C. Unchanged relaunch: REPEAT 8 (43, 109: falling). Estimate 2-3%.
- 22 launches cover 13 items. hd_tile (264 replicas) launched 3 times, 03:47, 04:29, 05:11, each preceded by
  "REPEAT ... FAIL_POSTCTS (6 attempts in 24 h) released only by a changed own input". The line is advisory
  under stops_off, so the launch follows anyway. hd_serdes, sle_su_l0, slw_su_l0, sle_ctl launched twice.
- cbn_q00__cldbcda913 reached attempt 18 on the same gen error (provenance.json / no src/export.signoff). The
  0358 fix C (0017e104f9) blocks item@N when attempt N failed on the same inputs. The leak: attempt 17 ended
  CANCELLED, and "RETRY-RELEASE ... ended (CANCELLED/-): released once" let attempt 18 launch 7 min later.
- Structural fix: the same-input comparison uses the last FAILED attempt, skipping CANCELLED and INFRA ones.
  For the advisory case: after 6 same-stage fails in 24 h the row launches only with a Fixes-Items commit or a
  changed fail key. That stops itself and needs no person.
- Owner: WAVE-PILOT-FIX. Items: HEAD-100 (hd_tile, hd_host_n), DIE-QC-103 (cbn_q00, cbn_q11 OT_XSTN_STRETCH).

### D. Source copies that fail every tick: SRC-SYNC to epyc2 failed 6 of 6 (new). Estimate 1-3%.
- "SRC-SYNC epyc10->epyc2 qwen_compute: copy rc=2 but the files are NOT on epyc2" at 04:48, 05:00, 05:07, 05:19,
  05:30, 05:40. The same 192 files copied fine to epyc7/8/10/intel1. epyc2 is therefore not a QC gen host
  (6 SRC-INCOMPLETE lines) and showed 22 idle threads at 05:35.
- epyc2 scratch2: 131 GB free of 880 GB, under its 150 GB floor, falling 17 GB/h (floor 50 GB in 4.6 h).
  The ot-store there is 419 GB by du. Whether rc=2 is the floor refusing the write is UNVERIFIED: the log does
  not carry the copy's error text.
- FLEET-OPS-R declined to move the store (05:43): the store is per filesystem so staging is a hardlink.
  5f45a94f549 (~/.config/ot-store/primary) is on main.
- Structural fix: (1) SRC-SYNC logs the first stderr line of the failed copy and, after 2 identical failures,
  stops retrying and posts once to FLEET-OPS-R. (2) On epyc2 the kw45 src trees and new jobs go to scratch3
  (887 GB free, store already there), so the small disk only drains. No store move is needed.
- Owner: FLEET-OPS-R (disk), WAVE-PILOT-FIX (SRC-SYNC error text and stop).

### E. Guard kills: 1 in 2 h (85, 51: fell). Under 0.5%.
- Only kill: epyc7 12:29 UTC, col_h9_r1__t1__cl49d7a23e__pv0bdbc3f3, openroad RSS 22 GB. Container name present.
  3 RESUME-MOVE lines "no die host admits 72 GB now". Part of the drop is the launch stop in A; re-check when
  S81 launches again.
- PLAN_BYPASS: 21 of about 470 admissions (4.5%, was 11%), all on epyc7/8/9, from lane scripts that set the
  env (example: fable-fix-kv-hg3 gate_bind.sh, 64 GB). Disk or admission refusals in the 6 admit logs: 0.
  refused.json is empty on 5 hosts, 1 entry on intel1.
- 0358 said kill attribution was missing. FLEET-OPS-R answered at 04:08 that it has been live since 4cac1136174d
  (33 of 35 kills named on epyc10). I accept that; my 0358 count of "81 of 85 not attributed" compared the wrong
  field.
- Owner: FLEET-OPS-R. No new fix.

### F. Wave tick: 332-634 s, median 503 s (922-1,163: fixed in part). Under 1% direct.
- 11 ticks: 634, 537, 514, 474, 422, 521, 591, 332, 488, 569, 503. The 332 s tick is the only one under the 400 s
  target. WAVE-TICK-1119 closed at 05:02 on that tick.
- What still costs: plan_dies 208-219 s and bind_preflight 207-216 s at 05:23 and 05:34. The preflight cache keeps
  a verdict while the plan + bind signature is unchanged, but the S81 stale verdict is recomputed every tick.
  loop_gaps 66-78 s, tool_skew 30 s, tools_lag 20 s.
- Structural fix: cache the stale verdict under the same signature as the green one. With A fixed the stale case
  mostly disappears.
- Owner: WAVE-PILOT-FIX (WAVE-TICK-1119 is closed).

### G. One job frozen 2 h and only reported. Under 0.5%.
- s81 serdes__t15__cla2127225 on epyc8: log frozen 391 min and "CPU 10,784 s not grown by 360 s for 120 min",
  21 processes, reported only (WF-1). dsdv_slice_lepe_mu_C__t1 is silent 477 min but its CPU grows: not hung.
  63 REAP-DEAD SILENT lines in the window are these two plus rows that are progressing.
- Structural fix: the watchdog acts only when BOTH tests hold for 120 min (no stage-log output and no CPU
  growth). That is the owner's 2-h rule and it cannot hit a busy job. It then relaunches from the last stage ODB.
- Owner: FLOW-HEALTH-1 (NOPROG-FIX-1115 code).

### H. Lane procedure slips (3 this cycle). Under 1%, one die run lost.
- DIE-LEVEL-CHECK-1119 edited proto_die_l.sh in place at 04:26 PST while the S81 and QC chains read it; S81
  l1119b exited 2 after its GRT. The lane now copies the script per run.
- A lane ran ot-run on a gen host that could not resolve its own name ("no host qualifies"). FLOW-HEALTH.tsv
  HOSTNAME-RESOLUTION at 05:08 shows all 7 hosts ok, so the host side is fixed.
- A lane rsynced scripts into a shared lane directory. I found no post naming it; UNVERIFIED which lane.
- Structural fix: ot-run copies the command's script into the job directory at submit and runs the copy, so an
  in-place edit or an rsync over the source cannot reach a live job. ot-run prints NOT-RUN with the failing
  check (name resolution) instead of "no host qualifies". Both make the slips harmless without a rule to remember.
- Owner: FLEET-OPS-R (ot-run), KIT-OPS-5 (lane brief text).

### I. Cleanup deleted a clock-of-record kit. One kit; under 0.5%.
- ot-auto-clean lane pass on epyc10, 11-18 19:04 PST, removed s81-die-r3-proto/kit_d7w_ecov3 (idle 20.3 h, no
  signed unit). FLEET-OPS-R found no other clock-of-record tree deleted on 6 hosts.
- 68ad9df0b11d (keep list covers clock-of-record kits) is on main and is NOT an ancestor of rt 0ad8719029d8.
  A grep of ~/.local/lib and ~/.local/bin on epyc10 and epyc2 for clock-of-record names found nothing, so I
  cannot confirm it is installed. Timers run every 30 min on both hosts.
- Structural fix: keep by reference. The delete guard keeps every path named in a die's plan_of_record,
  bind_of_record or clock-of-record JSON and in PROTECTED-DBS.txt. A name list has to be extended after each loss;
  a reference scan does not.
- Owner: CLEAN-ALL-1115. FLEET-OPS-R to confirm the install on all 6 hosts.

### J. Report noise that hides real lines (no fleet time)
- CELL-BIG: 3,599 lines, 77% of the window, 96 items, about 327 per tick since 04:44. cell_big_logged does not
  dedupe. DEDUP OFF RELEASE repeats the same 8 rows each tick (88 lines).
- FAIL-ROUTE relay, class 958ddd525b: 6 NEEDS-ACTION / NEEDS-LANE posts between 04:28 and 05:28 to 4 fix lanes
  and COORD. The "failures" are two triage RESULT tables from S81-FAILED-TRIAGE-1119. COORD closed the class at
  05:11; the relay still posted at 05:18 and 05:28.
  Fix: the relay counts a post as a failure only when its sender owns the job it names, and a COORD ACK or RULING
  naming the class closes it.
- TOOL-SKEW UNMEASURED s81_head 11 times: rt/385f61b5582a.manifest.json still missing (third window).
  TOOLS-LAG QC 1,365 commits (1,333), hbm 2,462. TOOLS-DECOUPLE-2 exists and pushed d604720e1f4 (in rt): kits
  now carry tools_rev.json and flow_refresh replaces stale tool copies. 0358 said I found no evidence of it; wrong.
- HUB-SYNC-FAILED 2: a lane left lanes/handoff/FABLE-FIX-QC-rows-stb-origin.json edited in the hub checkout.
- failure_breakdown: STALE 104, all HBM (parked, flat). Non-design rows: cancelled (superseded) S81 56, KV 21,
  HBM 102. The live check still names epyc4 (not fixed from 0358).
- PLAN-CONFIG-DRIFT QC only_items sle_ctl__cl503337ff__v1 / __cl67434795__v1: still open.
- kit_wave_blocked.tsv now has 23 rows and needs_lane.tsv 3 (were header-only): 0358 G landed.
- Owner: WAVE-PILOT-FIX (CELL-BIG, DEDUP lines), FLOW-HEALTH-1 (relay, failure_breakdown), HEAD-100 (pin manifest).

### K. Disk
- epyc2 scratch2 131 GB (floor 150). epyc10 scratch2 90% used, 764 GB free. epyc8 87%, 1,001 GB free.
  intel1 kw45 wrote 281 GB in the quota window (alert only). ot-store on scratch2: epyc10 802 GB, epyc8 558 GB,
  epyc9 498 GB, epyc7 476 GB, epyc2 419 GB, intel1 411 GB.
- Owner: FLEET-OPS-R.

## Did the fixes from FABLE-FLOW-0358 land?
- A keep superseded rows while the replacement is bind-stale: yes. Adoption gate: no. Class A is still open.
- B kills: fell 85 -> 1; attribution was already live.
- C block on same inputs: yes for FAIL -> FAIL; leaks through a CANCELLED attempt (cbn_q00 a18).
- D kill-pin only on the adopted tree: yes (WAVE-PILOT-FIX 04:10, rt f46a3a051bac). SRC_MANIFEST fails 0 (4).
- E stale in-kit tools: yes (d604720e1f4). No OT_NATIVE_CELL_CAP fail in the window.
- F tick: partly, median 503 s against a 400 s target.
- G tsv writers: yes. ORPHAN-DEAD wording and the epyc4 name: no.
- H intel1 scratch refusal: none this window.
