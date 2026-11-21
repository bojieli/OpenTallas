# FABLE-FLOW-2000: procedural / flow review, window 11-20 17:50 to 20:05 PST

Lane FABLE-FLOW-2000 (Fable 5.2). Read-only review, flow only. Previous: lanes/FABLE-FLOW-1800.md.
Sources: autopilot/log.txt (1,297 lines from 17:50), lanes/FLOW-HEALTH.tsv (19:08), tools/failure_breakdown.py (19:59,
read-only), ot-run --status (19:52), ot-heavy-reconcile --free and df on the 6 build hosts (19:54), kit_wave.json and
kit_wave_state.json (19:54), intel2 ot-run signals.log, lane posts and handoffs (FLEET-WATCH-1630, FLOW-NOADV-R3,
ADOPT-CENSUS-1800, S81-DIE-R5, BUILD-SETTINGS-AUDIT-1900, NOPROG-WATCHDOG, FLEET-OPS-R).
Marking: **V** = I read or measured it this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.

## Headline

1. **The sign-off count has not moved for 4 h 15 min (V): signed any plan 474, current plan 409, same as 15:46.**
   The fleet is full the whole time (idle threads 0 of 624 on all 13 ticks).
2. **Launches fell to 10 (hour 18) and 20 (hour 19), from 93 and 44 (V). The cause is memory, not the flow.**
   Every build host has 75 to 91 percent of its 1,008 GB in real use (MemAvailable 94 to 255 GB). Admission is
   MemAvailable minus the 48 or 64 GB floor minus the stage growth of running builds, which gives 0 to 7 GB.
   No disk refusal, no lock timeout, no docker block in the window. So the lever is what is running, class 1.
3. **A lane cancel is undone by the wave (V).** S81-DIE-R5 cancelled three D8i svc_rs rows at 19:34 on a COORD
   ruling. The wave recorded INFRA[stopped], gave each "one free retry" and launched attempt 17 two minutes later.
   Class 2.
4. **One row retries the same error every 8 minutes without limit (V):** s81 ot_s81sl_leaf__t28, six identical
   kit_rtl failures 19:23 to 19:59, attempt 7 next. The error is typed INFRA, so no stop counts it. Class 3.
5. Of the seven fixes asked about, four work, one works for one job only, two have produced no output yet. Table below.

## The 18:00 fixes: landed, and do they work

| Fix | Landed | Works |
|---|---|---|
| AUTOSTAGE | yes (V, in rt/current) | 1 job moved today (18:25, epyc10 to epyc7), 1 refusal (V, signals.log). |
| Waiter re-exec (RELOAD) | yes (V) | 2 RELOAD lines, both 19:49 (V). rt/current changed 18 times in hours 18 and 19, so most waiters did not reload: class 4. |
| --hosts spill | yes (R) | Not separable in the log. 7 SPILL-COPY-FAILED at 19:44 (epyc10 to intel1, lane gpltdab) (V). |
| Oldest waiter in --status | yes | Works (V): epyc8 19.9 h, epyc7 2.7 h, epyc2 1.0 h. |
| rt_pin for gates (a2a4cb2d35) | yes, file in rt/current (V) | Not exercised that I can see. Lane gate scripts must add the eval line themselves (R). rt/current moved 7 times in hour 18 and 11 in hour 19 (V), so an unpinned gate is more exposed than at 18:00. |
| tools_sha refusal | yes (R) | Not exercised. s81 tools_sha is still the word `j5tree` (V); TOOLS-LAG s81 is still unmeasured; s81_head pin manifest still missing (V). Works only at the next S81 apply. |
| ADOPT-DIFF / EVENT-CENSUS | yes (V, files in rt/current) | Works: 8 S81 hold_items carry the EVENT-CENSUS key (V); J5, QC V1 and KV D26 reports posted (R). Gap: unregistered reads unmeasured on 267 types (R). |
| Failed-stage logs kept | code in ot-job (V) | No output: `ot-job-failed-logs` exists on none of the 6 build hosts (V), with 4 place failures since it landed. Not confirmed. |
| PLACE-SETUP-STOP, PLACE-REGION (6829d05470) | yes, pushed 19:29 (R); in rt from about 19:43 | 0 stops so far (V log; R owner sweep 19:51). Kits take their tools from rt at launch (V: launch tree `<src>@<rt sha>`), so only the 11 or so launches after 19:43 can show it. Neither tcl path has run under OpenROAD yet (R). |
| epyc7 docker breaker | yes (V) | Not triggered: no `docker.broken` on any host, `docker ps` 0.07 s on epyc7 (V). epyc7 is now held by memory (914 of 1,008 GB used), 21 waiters / 891 GB. |
| STOPPED-OUTSIDE (cancel is not OOM) | yes (R) | Does not reach the wave: class 2. |

## Classes

### 1. Full fleet, flat count: jobs that cannot sign keep their memory

- Count, trend (V): 312 running jobs (stall_watch 19:50). Wave rows: 202 in route, 86 before route, 139 route-held.
  Of the 213 enqueued rows, 106 started over 12 h ago and 85 over 24 h ago. 108 are on a superseded event.
  NOPROG-WATCHDOG 19:45: 40 of 305 containers flagged: 39 GRT-LABEL design-fail (examples: overflow 81,748 and 50,446
  at round 10; GRT-0273 clock NDR dropped) and 1 UNSIGNABLE (setup -338.84 ps). 29 jobs are over 6 h in one stage.
  Waiters: 77 asking 3.75 TB (epyc8 27 / 1,926 GB, epyc7 21 / 891, epyc10 11 / 240, epyc2 10 / 396, intel1 7 / 272).
  REQUEUE lines 92 and 105 per hour: each waiter is placed again every 120 s and finds no host.
- Root cause: the label has no consequence. The watchdog cancels only the UNSIGNABLE verdict (setup below -300 ps).
  A GRT-LABEL row is "label only, the job keeps running". Old-event rows are kept because they may still sign, which
  is right, but nothing separates the ones that are measured unable.
- Structural fix (P), no new gate: NOPROG treats a GRT-LABEL row as UNSIGNABLE when the job is over 3 h old and two
  reads 30 min apart show overflow above 1,000 at round 10 or later and not falling. That is the "flat repair" case
  of the owner rule of 11-20. It posts the evidence line and cancels the exact unit, as it does today for setup.
  The row then goes to the die owner as a PLAN row, not back to the wave.
- Owner: NOPROG-WATCHDOG for the verdict, BUILD-SETTINGS-AUDIT-1900 for the threshold.
- Fleet time: 39 of 305 containers, about 13 percent (I; by container count, not by GB).

### 2. A cancel by a lane is relaunched; rows of two events share one name

- Count (V): 5 FAIL lines today read `INFRA[stopped] ... ot-run --cancel`, 4 in this window (qc cbx_q10 19:05;
  s81 svc_lo_dsdv_svc_rs t2, t5, t6 19:34). All got INFRA-FREE-RETRY. svc_lo t5: cancelled 19:34:39, LAUNCH 19:36:53
  as attempt 17 with event key 224567138ab (J5). The cancelled attempt 16 was a D8i row (465cb9fe2d3).
  29 INFRA-FREE-RETRY lines today in all.
- Name sharing (V): 69 live item names exist on more than one event (S81 43, QC 25, HBM 1). S81 has live rows on 4
  events. Attempt numbers run across events (a16 D8i, a17 J5). hold_items, retry keys and cancel marks match the
  item name, so none of them can target one event (R, S81-DIE-R5 19:20, and I agree).
- Root cause: the wave reads the signal, not who sent it. `ot-run --cancel ... --reason` writes its reason in the
  kill line and the wave still files it under infra. The cancel of a D8i row then frees the name for a J5 launch.
- Structural fix (P):
  - A kill whose sender is `ot-run --cancel` is state CANCELLED with the given reason, never INFRA, never a free
    retry. The row relaunches only on a changed plan block or an explicit retry key.
  - Row identity is (item, event) everywhere a person names a row: `item@event` in hold_items, retry keys, cancel
    marks, unblock lines. A bare item name keeps today's meaning (all events), so nothing existing changes.
  - The attempt counter is per (item, event).
- Owner: FLOW-NOADV-R4. Fleet time: under 0.5 percent now; the cost is that a COORD ruling does not hold.

### 3. Retries on an unfixed cause

- Count, trend (V):
  - s81 ot_s81sl_leaf__t28: `reset_tree.ResetError: reset relay -> u_lf.u_ve.u_s.rst_n exceeds reach (176.76 um)`
    at kit_rtl, 6 times from 19:23, one launch per tick. Typed INFRA[tool_mix]. RETRY-HOST says "the last attempt was
    killed" and moves it to another host each time. Nothing was killed.
  - Live rows by attempt: 78 of 441 at attempt 10 or more, 30 at 15 or more, 8 at 20 or more. Highest: 46
    (dsdv_slice_c1x_C__t6, old event, in route with GRT overflow 81,748), then 30, 30, 25, 24.
    On the current events: 32 of 290 items at 10 or more, 18 at 15 or more, 3 at 20 or more.
    The known "attempt 22" is not the top of the range.
  - FAIL lines 12 (hour 18: 4, hour 19: 8); previous window 11. 4 are the cancels of class 2, 5 are t28,
    4 are place errors (MPL-0020 twice, DPL-0033, CLAND band).
  - REPEAT-STOP still prints "OOM kill; the resubmit runs with place memory x1.5" (2 in the window: qc slw_fe_v1
    18:21, s81 leaf t31 19:05). I did not check whether either was a real OOM.
- Root cause (V + R): the stop counts one signature in a row. INFRA never counts. A changed input digest resets the
  count. And any Python exception in a kit tool is typed INFRA "tool or source skew", including a typed design
  error raised on purpose (ResetError, ContractError, ValueError from the plan check).
- Structural fix (P):
  - A typed refusal from a die tool (an exception class of the tool's own, same message twice) is PLAN, counted,
    and stops at the third, like station_overlap since ccc542c1af. INFRA is only: host, signal, disk, copy.
  - Total cap per (item, plan block): 8 failed attempts of any class. INFRA counts after the second one on a
    second host. The cap is released by a changed plan block or by a PROVEN_FIXES row for that family, not by any
    digest change. FLOW-NOADV-R4 is building this; the two points to add are "INFRA counts" and "per event".
  - RETRY-HOST only after a recorded kill (the kill-cause function asked for at 18:00, class 4 there, still open).
- Owner: FLOW-NOADV-R4. Fleet time: t28 under 0.2 percent but without end; rows at attempt 10 or more are 18 percent
  of live rows (I: their share of memory was not measured).

### 4. Runtime changes every 4 minutes

- Count (V): new rt directories per hour today: 2 to 5 until 17:00, 7 in hour 18, 11 in hour 19, 3 in the first
  8 min of hour 20. Tick time 286 to 494 s; kit_wave_step is 245 to 440 s of it. Each launch tick mirrors a new
  launch tree to the gen hosts. epyc10 holds 540 launch trees.
  Hub clients: 327 ot-run processes; 30 on rt 315cc722d686 and 26 more over 12 h old.
- Root cause: every push to main makes a runtime, and 36 pushes ran in the window. Nothing batches them.
- Structural fix (P): the rt sync publishes at most one runtime per 15 min (the newest main), unless a push carries
  a `Flow-Urgent:` trailer. Launch trees older than 24 h with no live job are removed by the existing cleanup.
- Owner: FLEET-WATCH-1630. Fleet time: none measured; it is tick time and the exposure of unpinned gates.

### 5. epyc8 waiters

- Count, trend (V): 27 waiters / 1,926 GB, oldest 19.9 h (17:48: 32 / 1,916 GB). Flat. epyc8 load 294 to 325 on 96.
- Judgement: this is no longer a flow fault. No host admits more than 7 GB, so there is nowhere to move them, with
  or without AUTOSTAGE. The 9 route kits of 96 GB (D8i) are waiting for memory that class 1 would free.
  The 18:00 request stands for the lane jobs: their owners re-submit (S81-DIE-R4 hop.tcl, the 3 count.sh).
- Owner: FLEET-WATCH-1630. Fleet time: compute 0.

### 6. Hand patches with watchers

- Count (V + R): 1 case in the window. S81-DIE-R5 patched serdes kits by copy+mv and ran serdes_watch.sh on 6 hosts
  from 19:19; all 6 were stopped at 19:55 after 6829d05470 reached rt (36 min). 0 such processes on 5 hosts (V).
  The handoff names two more watchers (GRT, PLACE-SETUP-STOP). pgrep-loop shells: 85 on 5 hosts (17:48: 86 on 6).
- Judgement: this one closed the right way, by a flow fix, and fast. The open risk is serdes kits generated before
  19:43: they carry neither the hook nor, now, the watcher patch. S81-DIE-R5 should list them.
- Structural fix (P): `kit_wave_edit kit_hook <die> <family glob> <stage> <tcl file>`. The hook is copied into every
  kit of the family at gen, its digest is part of the input hash, and it is listed by the settings audit. A lane
  fix is then one recorded config line that later kits inherit, and no process has to watch for kits.
- Owner: FLOW-NOADV-R4; BUILD-SETTINGS-AUDIT-1900 lists hooks with the env keys.
- Related (R, BUILD-SETTINGS-AUDIT-1900 19:51): 94 `__pv` / `__pad` variants do not inherit the parent item_env.
  Same fault: a setting made by hand reaches the rows that existed that day and not the next ones.

### 7. Holds that over-hold, parked die, unowned

- WAIT-VISUAL (V): 49 rows at 17:51, 67 at 19:38, peak 72, while the auto reviewer accepts 2 to 8 per tick.
  WAIT-FORM 38, flat for 2 h. The owner rule of 11-13 is that a visual verdict gates sign-off, not route.
  With memory full these rows would only queue, so the cost today is small; the rule is still not what runs.
  Owner: FLOW-NOADV-R4.
- HOLD-AUDIT is clean on all 13 ticks (held-but-launched 0, zero-match 0). S81 hold_items 107, QC 30, KV 8.
- HBM is parked and still enabled (V): DIE-OFF "plan of record unreadable" each hour, ALERT ADOPT-GUARD 26 times
  in the window, TOOLS-LAG and TOOL-SKEW lines each tick, 104 of the 107 STALE rows. P: a `parked` flag on the die
  that stops its alerts and takes it out of STALE. Owner: FLOW-NOADV-R4.
- STALE current-event 105 (17:46: 104). QC 2: sle_hc1__cl7d360508 (KIT-WAVE-1), sle_hc0__cl929603c0__cl38badc56
  (unowned, new). KV 1: core qkd_pv_fin_s8_pin, unowned for the third review. Owner: QC-PLAN-R7, KV-PLAN-R2.
- Non-design rows (V): KV other flow error 4, PDN-0006 2, bind stale 1, kit input missing 1 (kv3_hub_C).
- Alerts to nobody (V): AUTO-CLEAN epyc10 "no pass for 151 min" posted 8 times with no reply; the timer shows a run
  at 20:01, so the alert or the timer record is wrong. Lane quota alerts for kw43-wave on intel1 ask "owner please
  prune or confirm" of a wave that has no person. Owner: FLEET-WATCH-1630.

### 8. Disk, admission, push gate

- Disk (V): no refusal in the window. intel1 scratch2 is 272 GB free at 19:54, up from 202 at 18:17: the sub-step
  prune removed 65 GB fleet-wide in the window and RECLAIM-SWEEP reaped 27 attempts. The fall of 11 GB per hour did
  not continue, so the 98 GB of HARVEST DBs do not need an owner ruling tonight.
  The next stop is epyc2: root 91 percent, 325 GB free, down 35 GB since 18:40 (28 GB per hour). ot-run stops
  admitting on a scratch root at 95 percent, about 5 h away at that rate. epyc8 and intel1 scratch are at 93 percent.
- /var/tmp/ot-heavy holds 23,000 to 30,000 state files per host (V), mostly `thr` and `meta` of ended jobs.
  P: the reconcile pass removes the files of a scope that no longer exists. Owner: FLEET-WATCH-1630.
- Copy-back (V): 1 FAIL "place RC=0 but no 3_place.odb: ot-run moved the job, no copy-back record" (t28, 19:15).
  P: a moved job writes its copy-back receipt before it reports RC; the wave reads the receipt, not the file.
- Push gate (V): 36 ot-push-main runs, 6 died (5 with rc 4 after 578 to 843 s, 1 with rc 3): 17 percent, about
  1 h of lane wall time. One order-dependent test is known (R, test_class_stop). Two jobs posted under the lane name
  `lanes`, so OT_LANE was set to a directory name. Owner: FLOW-NOADV-R4.

## Fleet time, summed

| Class | Share |
|---|---|
| 1. Running jobs with a design-fail label | about 13 percent of containers (I) |
| 3. Rows at attempt 10 or more | 18 percent of live rows; memory share not measured |
| 2, 3 (t28), 8 | under 1 percent together |
| 4, 5, 6, 7 | lane and tick time only |

## Do now (ordered)

1. NOPROG-WATCHDOG: GRT-LABEL with flat overflow above 1,000 on a job over 3 h becomes UNSIGNABLE with evidence.
2. FLOW-NOADV-R4: `ot-run --cancel` is CANCELLED, no free retry; typed tool refusals are PLAN and counted;
   total cap counts INFRA and is per (item, event); `item@event` in holds and keys.
3. S81-DIE-R5: stop the t28 loop at its cause (reset reach 176.76 um on leaf t28) and list serdes kits generated
   before 19:43.
4. FLEET-WATCH-1630: one runtime per 15 min; confirm one failed-logs directory; epyc2 root before 95 percent.
5. S81-J6-ASSEMBLY: set s81 tools_sha to a real sha at the J6 apply (asked at 14:00, 16:00, 18:00).

Not checked: whether the two REPEAT-STOP memory raises were real OOM kills; the memory held by the 39 labelled
containers; the age of each WAIT-VISUAL row; what rc 4 of ot-push-main means; any gate lost to a runtime change in
this window; why failed-logs wrote nothing; whether rt cca022294010 (19:34) already carried 6829d05470; localhost
and intel2 waiters; git history (no git run in the owner checkouts).
