# FABLE-FLOW: flow and procedural review, 17:40 to 19:48 PST 11-19 (read-only)

Sources: autopilot/log.txt (1,196 lines in the window, 11 ticks, plus the tick that started 19:45), kit_wave_state.json,
kit_wave.json, lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py (ran, 19:44), ot-run --status (19:43, 19:48),
rt/history.log, hub git mirror (origin/main f22d0e5f722), user units on intel1/epyc2/epyc7, disk-rate.log,
FABLE-FLOW-1803.md. Fleet 624 threads x 2.1 h = about 1,300 thread-hours. Shares are estimates unless marked measured.

Not checked: the 8 test_kit_wave.py failures (tests not run; no commit on main in the last 3 h names them), and the
behaviour of REAP after the 19:45 tool switch (that tick had printed no REAP line by 19:48).

## Numbers
- LAUNCH: 17h 1, 18h 78 (QC 36, KV 38, HEAD 4, S81 0), 19h to 19:39 11 (S81 0), then 179 in the 19:45 tick (S81 175).
- KIT-WAVE FAIL 9 (10 in the prior 4 h): all PLAN at gen/place on 3 rows (sle_su_l0__cl7a55c676 x5, qkd_pv_fin_s8_pin x3,
  kv3_hub_Wi x1). No INFRA, no OOM, no EARLYOOM in the window (3 OOM in the prior window).
- DIE-OFF 14 (s81 7, hbm 7), NO-LAUNCH 6 (s81_head, 1 row), SKIP-SAME-INPUT 20 on 4 rows, REAP 164, REAP-REVIVE 29,
  ORPHAN stopped 12, ORPHAN-DEAD 1, KIT-LOST 6, BAD-HOSTS 5 ticks (epyc7 4, epyc9 1), UNDER-USE idle 60-82 threads.
- failure_breakdown: signed any plan 473, current plan 408. STALE 105 current-event rows (S81 85, all CANCELLED
  SUPERSEDED 13:08-13:40 and never relaunched) + 84 on superseded blocks. Non-design classes in the open list: S81
  "cancelled (superseded)" 13, KV 1, HBM 90 + 12 cores; "other flow error" QC 2, KV 1.
- Disk and admission: 0 disk refusals and 0 admission refusal lines. epyc8 admits 0-2 GB (load 257-267/96, 577-581
  threads asked); every other host admits 21-127 GB. Hub root 120 GB free (74%); epyc2 scratch2 113-129 GB free.
- Tick 398-598 s (kit_wave_step 320-460 s); no tick killed.

## Did the 1803 fixes land
- A (S81 stall): fixed 19:34-19:45, see class 1. Preflight now parks BIND_STALE rows as WAIT-BIND (46 lines 18:16):
  landed. Automatic bind regenerate: NOT landed.
- B (silent no-launch): DIE-OFF / NO-LAUNCH per-tick lines landed cdba42d317a (first line 18:26). KV-D25d launches again
  (36 RUNNING). The lines have no duration and raise no alert; see detector.
- C (waiter re-pick, pick hosts under their cores): NOT landed. Worse: epyc7 load 361-407/96.
- D (OOM never blocks): landed (cdba42d317a, 11f7c845850). PREGRT_HOLD rc 137 rerun: not seen in the window.
- E (units in lane dirs): landed for ot-retire-superseded (ExecStart under rt/current on intel1, epyc2, epyc7; last run
  rc 0 at 19:11). Hourly 203/EXEC scan: not seen. One cron on the hub still pins rt/d0ee4a2afb10 (limit_outage.py).
- F (a6ae56f851): in rt/current since 19:45.
- G (self-heal stop, KIT-LOST checks the gen host): NOT landed; ITEM-SYNC phy_serdes_b rc=2 every tick (12x), KIT-LOST 6.
- TICK-KILLED ExecStopPost: NOT landed (TimeoutStartSec=3000, no ExecStopPost).
- All ten 18:00 fixes (5b4185d13c, 7d70942a11, 7ceb18083b, 11f7c845850, 8b1909473d6, a2fb7e625dd, 2f306028d5,
  4a972ca112f, a6ae56f851, f0fe518fb5e) are ancestors of rt/current f22d0e5f7228, but only since 19:35-19:45. Every tick
  in this window except the last ran without them. RETRY-KEY-LAUNCH worked at 19:11 (cbn_q11 x2).

## Classes, ranked by time wasted

### 1. S81 launched nothing 14:52-19:45 (4.9 h; 2.1 h in this window). Schedule loss, not machine loss.
- The known cause is only half right. b4bb6a8b1e9 was not an unpushed commit: it was a synthetic event key that never
  was a commit (coord 9d1f3e575c2). The die gate ran git ancestry on it, could not resolve it, and turned the die off.
  14:52-18:26 there was no line at all; 18:26-19:32 seven DIE-OFF lines, no alert, and a lane fixed it by hand:
  S81-DIE-R3 made event record commit b05c98f7919 on main (19:33), WAVE-PILOT-FIX made the gate fail open (f0fe518fb5e).
- Verified: 175 S81 launches in the 19:45 tick, 0 DIE-OFF s81.
- Root cause: kit_wave.json accepts any string as a die event; the check that needs a commit runs later, every tick,
  and its failure meant "off".
- Structural fix: validate at write time. coord-commit.sh (or adopt-guard-pretick) refuses a kit_wave.json whose
  dies.<die>.event does not resolve in the hub mirror, unless the die declares event_kind=label. The class cannot enter.
- Owner: WAVE-PILOT-FIX. Share: 0% machine (old-event rows filled the hosts), 4.9 h of S81 current-plan throughput.

### 2. The wave stops its own live job: "row@N superseded by attempt N of the same item". 13 live jobs in 2 h.
- Each case: REAP-REVIVE "queue job still live past synthesis: row revived, units kept", then 2-14 s later REAP of the
  same row "superseded by attempt N of the same item; units ['ap-<job>-a1']" with the same N. The job is then found by
  ORPHAN / ORPHAN-DEAD 10-60 min later, KIT-LOST ("run_kit.sh missing on the hub"), and the row restarts from gen.
- Count: 13 with live units in the window (17:51 x2, 18:02 x2, 18:33 x7, 19:07 x2); 24 lines today (09h 6, 13h 1,
  16h 4, 17h 2, 18h 9, 19h 2). QC 11, KV 1, HEAD 1. sle_st_a_v1__cl989804f6__cl18eece69 lost attempts 2 and 3 this way
  (16:00, 18:33) and made no progress for 3.3 h; tt_ctlm lost two (17:51, 19:07).
- This is the same-event form of known item 2, not only the cross-event form. 5b4185d13c (own_job) reached rt at 19:35,
  after the last case; whether it covers the same-item form is UNVERIFIED.
- Structural fix: one invariant in the reaper: a row is superseded only by a strictly higher attempt number, and a unit
  is stopped only when the job id recorded in that unit differs from the surviving row's job id. Add a test with
  attempt N vs N.
- Owner: WAVE-PILOT-FIX (verify on the 20:00 ticks). Share: about 3-6% (13 jobs x 16 threads x 15-60 min, plus restarts).

### 3. Host imbalance, unchanged since 1355. Idle 60-82 of 624 threads (10-13%, measured) with 2 hosts far over.
- epyc7 load 361-407 on 96 cores, epyc8 257-267/96 and admits 0-2 GB, while epyc2 idles 60-67 threads. epyc7 was
  BAD-HOSTS in 4 of 11 ticks, so stop/reap/orphan checks skipped it. Admission is by memory only, so a host with free
  memory keeps taking 16-thread jobs at 4x its cores.
- 21 GEN-HOST-TREE lines at 19:46: epyc7 lacks the S81 d8h tree, rows redirected to epyc2 (self-healed, but the tree
  was never synced during the 4.9 h the die was off).
- Structural fix (choice of host only, no cap): the pick orders hosts by load/cores before admit GB, and ot-run moves
  a WAITING job to another admitting host after 2 polls at 0.
- Owner: FLEET-OPS-R (ot-run), WAVE-PILOT-FIX (pick). Share: 10-13% idle, plus slowdown on epyc7/epyc8 not measured.

### 4. Relabel of an unchanged plan re-arms every repeat counter. New.
- The switch b4bb6a8b1e9 -> b05c98f7919 changed only the event key (same tree, same plan 8dfedade987b). Result: 46
  fail_keys + 46 fail_sigs dropped (FAIL-STALE), 50 REPEAT-STOP RELEASE "inputs:block", and 20 S81 rows that were
  STALLED (6 attempts in 24 h at route or post-CTS) relaunched unchanged.
- Root cause: the event label is part of the row input digest and of the fail-key scope.
- Structural fix: digest and fail keys use plan sha + src tree + tools; the event label is display only.
- Owner: WAVE-PILOT-FIX. Share: up to 20 repeat route attempts (about 1-2% if they fail as before).

### 5. Leaked scopes of CANCELLED attempts: 11 stopped at 19:19 after 17-28 h (cpu 0.00).
- epyc9 4, intel1 5, epyc8 1 (+1 real duplicate). They held no CPU; memory held is not measured. The orphan sweep had
  not removed them for a day and skips a host whenever it is BAD-HOSTS (class 3).
- Structural fix: REAP of a row confirms the scope is gone in the same pass (stop, then verify by unit name) and keeps
  the row in a STOP-PENDING list until it is; the sweep is then only a backstop.
- Owner: WAVE-PILOT-FIX. Share: under 1%.

### 6. Loops and alerts that never stop (noise that hides real lines). Under 1% machine.
- hbm (parked): DIE-OFF every tick + 24 ADOPT-GUARD alerts in 2 h. A parked die should carry parked=true and print
  one line per day; today it trains readers to ignore DIE-OFF. Owner: WAVE-PILOT-FIX.
- ITEM-SYNC phy_serdes_b 12x (37+ since 13:55), KIT-LOST 6: 1803 G, not landed. Owner: WAVE-PILOT-FIX.
- sle_su_l0__cl7a55c676 launched and failed at gen 5x with the same ContractError ("no SIGNED mean clock" in the QC
  view lib); qkd_pv_fin_s8_pin 3x. Cheap (gen), but kv3_hub_C waits on the latter (WAIT-CHILD 9x). Design owners
  DIE-QC-103, KV-102 own the input; the wave side is fine.
- HUB-SYNC-FAILED 7 alerts on 3 different files (FABLE-FIX-QC.md since 11:48, FABLE-FIX-KV-HG-rows-d24.json,
  QC-PADLEG-rows.json): lanes write row files into the hub checkout without coord-commit. Fix: the launch-row helper
  writes through coord-commit.sh, or reads row files from a non-tracked directory. Owner: FLOW-HEALTH-2.
- DISK-RATE log lines carry no timestamp, so "intel2 floor in 1.4 h at 60 GB/h" cannot be dated. Owner: FLEET-OPS-R.

### 7. Tool skew and lag. 0% now.
- TOOL-SKEW WARN s81 368, qc 357, kv 2 modules; s81_head UNMEASURED (pin manifest 385f61b5582a missing, eighth
  window). TOOLS-LAG qc 1,473 commits: the die is still on N46C / eb1e73448bd0, so the N46Q move (item 6) has not
  been adopted. hbm 2,582, head 466, kv 215, s81 167.
- rt/current switched 7 times in 19:35-19:45. Fixes merged 18:15-19:37 waited for a lane to switch rt.
  Fix: rt follows main automatically when the wave tests pass, which needs item 8 (FLOW-HEALTH-2) closed first.

## One generic detector: PROGRESS-WATCH (state based, not log based)
Run each tick from kit_wave_state + OWNERS, one line per finding, ALERT + NEEDS-LANE post on first hit, repeat hourly:
1. NO-PROGRESS <die>: enabled, not parked, eligible rows > 0, and 0 LAUNCH for 60 min. Print minutes since the last
   launch and the reason histogram. Would have fired for S81 at 15:52 (3.9 h earlier) and for KV-D25d at 14:08.
2. SELF-STOP <row>: the wave stopped a unit within 30 min of its own SUBMIT or REVIVE of that job, or stopped a row
   for an attempt number that is not higher. Would have fired 24 times today (class 2).
3. NO-ADVANCE <row>: 2 or more attempts ended by the wave or by infra in 6 h with no later stage reached.
4. STUCK-STATE: rows CANCELLED SUPERSEDED on the current event with no successor row for 60 min (85 S81 rows today).
Owner: new small lane, or WAVE-PILOT-FIX after class 2. The existing DIE-OFF / NO-LAUNCH lines are the inputs; what is
missing is duration, a parked flag, and escalation.
