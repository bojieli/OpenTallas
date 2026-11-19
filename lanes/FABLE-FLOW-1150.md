# FABLE-FLOW: flow and procedural review, 07:55 to 11:50 PST 11-19 (FABLE-FLOW-12xx, read-only)

Sources: autopilot/log.txt (4,615 lines in the window), kit_wave_state.json and state.json (11:44), auto_resign_state.json,
tools/failure_breakdown.py (11:47), ot-run --status (11:46), rt/history.log, ps and /var/tmp/ot-oom-age/kills.log on all 6
gen hosts (epyc7 answered once, at 11:47), lanes/FLOW-HEALTH.tsv, lanes/posts/WAVE-PILOT-FIX.md, git log of main, FABLE-FLOW-0755.md.

Window totals (last window in brackets; this window is 3.9 h, the last was 2.2 h): LAUNCH 532 (444): S81 445, QC 81, KV 3,
HEAD 3. FAIL 202 (247): S81 195, QC 7. By hour 08/09/10/11: launches 210/183/8/49, fails 53/105/10/34. REPEAT 390 (63).
Guard kills in the window: 0 on 6 hosts. Threads used 76-98%. Count: signed any plan 405.
Waste shares are estimates; none is measured exactly.

## Ranked by fleet time wasted

### A. epyc7 is still off the fleet: the old snapshot copies were never ended. Estimate 13-15%, flat for 5 h.
- epyc7 load 794 (08:02), 1,194 (08:59), 1,213 (09:18), 1,074/96 at 11:47. It carries 96 of the 624 wave threads.
  ot-run gives it "admits 0 GB". 45 wave jobs are RUNNING on it; 22 RETRY-HOST lines name it; REAP-DEAD cannot read it.
- Cause, seen in ps on epyc7 at 11:47: 1,004 "rsync --server" processes, 500 of them in state D (disk wait), nvme1n1
  at 90% util. By age: under 1 h 140, 1-2 h 4, 2-3 h 62, 3-4 h 368, 4-5 h 358, over 5 h 72. So 860 of 1,004 started
  before the fix reached the tools tree (08:20). Clients: intel1 190 (snapshots 3cb1702b 82, 63392233 89, addb6f0b 16),
  epyc2 31, epyc8 32, epyc9 43, epyc10 43. The oldest is 17,948 s old (started 06:47).
- Fix A of 0755, items 1-3, landed: 1eccc0936b3 (main 08:18, rt 08:20). It works where it runs: the 2 copy fails from the
  new code are class INFRA and carry "flock -w 7200 <snap>.push-epyc7.lock timeout -k 30 2400". No new storm.
- Two things did not land:
  1. Item 4 (end the leftover copies) was never done. No lane took it before the usage limit at about 09:00.
  2. A running unit keeps the tools tree it was launched with. Of 468 live run-item units, 246 run trees older than
     1eccc0936b3 (544353b1ff38 142, 7293a6df008c 64, 18cb3bfd585b 40). They still start the old copy with no lock and
     no timeout. Result: 88 more copy fails in the old form, class FLOW, after the fix (08h 30, 09h 54, 11h 13),
     against 2 in the new form. intel1 shows 8 old-form copies of 3cb1702b under 1 h old.
- Copy fails in the window: 90 to snaps/ (63392233 66, 3cb1702b 10, e2148ede 7) and 9 more mkdir timeouts, all with
  destination epyc7. 49% of the window's fails.
- epyc7 tools: rt/current there is 67c25c671d91 (06:31). It missed all 11 promotions since; each one logs
  "epyc7 FAILED ssh".
- Structural fix (no hold, no launch cap, no job touched):
  1. One-time: end the rsync clients whose row is already FAIL or relaunched (the copy is not a job; the row has a newer
     attempt). About 420 clients on 5 hosts. I did not touch them (read-only).
  2. The snapshot push is run as `rt/current/tools/autopilot/kit_wave_roam.py push` at call time, not from the unit's
     own tree, so a copy fix reaches running units at once.
  3. A row is not given a kit host that is unreadable or over 2x cores while another host has the snapshot verified;
     the pick already knows this (RESTAGE-PICK prints epyc7 room=0).
  4. A host that missed a promotion gets it on the first run that reaches it (ot-tools-sync retries the missed sha list).
- Owner: FLEET-OPS-R (1, 4), WAVE-PILOT-FIX (2, 3).

### B. Tick time: median 702 s (was about 650), one tick of 2,581 s. Estimate 2-3%.
- 14 ticks: 356, 420, 483, 485, 600, 633, 660, 744, 841, 853, 976, 1,000, 1,093, 2,581 s. Target 400 s: met once.
- The 2,581 s tick (10:11-10:54): the log is silent from 10:16:24 to 10:47:32, then "SRC-SYNC qwen_compute: 132 missing
  input file(s) copied epyc10->epyc7". The self-heal copy to epyc7 held the tick for 31 minutes. Launches in hour 10: 8.
- Other costs that are epyc7 waits: stop_cancelled_rows 122 s in 4 ticks (one ssh timeout), reap_dead 122-297 s,
  reap_stale_attempts 132-201 s, poll_running 163 s and 292 s, collect 221 s.
- Fix H of 0755 landed (432200e074b, skip a host after 2 ssh failures in a tick). It does not cover these paths.
- Structural fix: SRC-SYNC and ITEM-SYNC self-heal, stop_cancelled_rows and reap_* read the same per-tick bad-host list
  and skip a host that is unreadable or over 2x cores; the self-heal copy runs detached under `timeout`, as the REAP
  probes already do.
- Owner: WAVE-PILOT-FIX.

### C. Usage-limit stall, about 09:00-11:40. No machine time lost directly; it froze A and B for 2.7 h.
- Lanes posting per 15 min (LIMIT-GUARD): 13 at 09:00, 7 at 09:15, 2 / 3 / 1 at 10:15 / 10:30 / 10:45, 7 at 11:45.
- Main had no commit from 08:55 to 11:47 (rt/current is b098cf029b18 since 09:07).
- Kept running (no LLM): 14 autopilot ticks, 240 launches after 09:00, BOUND-FALLBACK each tick, RESTAGE 76,
  HUNG-WATCH 4, REAP 102, SRC-SYNC self-heal, ot-tools-sync, cleanup crons. Threads stayed 81-95% used.
- Stalled: every code fix (class A items, class D below), 220 S81 FAIL rows that wait for a changed input, the visual
  verdicts, and the epyc7 repair. LIMIT-GUARD only counts; it acts on nothing.
- Structural fix: the two repairs that needed no judgement go into no-LLM timers so they do not wait for a lane:
  the leftover-copy reaper of class A (a copy whose row has a newer attempt or is FAIL ends) and the missed-promotion
  retry. LIMIT-GUARD posts one line when the count is 3 or less in 2 reads, with the open READY/FIX list. No hold.
- Owner: FLEET-OPS-R.

### D. KIT_TOPOLOGY_BIND_STALE: 76 fails on 75 S81 items. Under 0.5%.
- By hour 20 / 41 / 3 / 12. By family: col_h9_r1 19, col_h9_r2 19, col_h10_r2 12, col_h10_r1 8, leaf 8, col_h10_r0 6,
  col_h9_r0_p1 4, other 4. Each item fails once, then BOUND-FALLBACK launches it on tree d8f (14 fallback lines, 556
  row listings).
- All 39 fails with a launch in the window were launched on the live tree d8g. Launch to fail: median 8 min, p90 11,
  max 23. About 10 job-hours in all.
- Cause in the process: the hub bind preflight passes the row on d8g, and the kit-time check ("native source
  stage/reset realization differs") refuses it 8 minutes later. Two checks, two answers. The row is then a FAIL of class
  PLAN and counts in the repeat and breaker counters.
- Structural fix: bind preflight runs the same kit_topology comparison per row, so a stale row goes to BOUND-FALLBACK in
  the same tick with no launch and no FAIL row. The canonical native bind for d8g is the die fix.
- Owner: WAVE-PILOT-FIX (in work), DIE-S81-92 (bind of record for d8g).

### E. Source copy to epyc2 still fails every tick: 30 lines (16). 1%.
- Fix D of 0755 landed (4578f44a345, tar dereferences hard links). The same error is still logged at 11:43 on
  b098cf029b18: "Cannot open: Invalid cross-device link", 30 of 30 lines. epyc2 has 15 SRC-INCOMPLETE lines for QC
  (bind_cells.sv missing). The fix did not work. Stop after 2 identical errors: not landed.
- UNVERIFIED cause: the link is made on the epyc2 side (kw45 is a symlink to scratch3), not in the tar stream.
- Structural fix: the receiver resolves the destination with realpath and writes plain files there; one test with a
  destination that is a symlink to another filesystem.
- Owner: WAVE-PILOT-FIX.

### F. Unchanged relaunch: REPEAT 390 (63). 1-2%, falling.
- By hour 59 / 226 / 95 / 1 / 9. Most carry "same fail key (FLOW @pipeline)": these are the old-form copy timeouts of
  class A, which are FLOW and not INFRA. SKIP-SAME-INPUT 93, REPEAT-STOP 30, RELAUNCH-ON-FIX 134.
- Still repeating on a design key: ot_s81sl_leaf__t56, __t54__cl501e5681, __t40__cl86ea32b3 (5 each).
- No new fix. A.2 removes the cause. Items: DIE-S81-92.

### G. QUEUE-REPICK (c24b7e15d3b, rt 08:57): fired 0 times. No waste, no gain.
- No row qualifies: all 255 ENQUEUED rows with a queue job have a started job (RUNNING 255; epyc7 45, epyc2 67).
  The rule moves only jobs that have not started. The older RESTAGE path moved 76 unit waiters, 22 of them off epyc7.
- The real loss on epyc7 is started jobs that crawl; no rule may cancel those past synthesis, and none should.
- epyc2 is now the next host over the line: load 261/128, 914 threads asked, 94 running. Re-read next window.
- Owner: WAVE-PILOT-FIX. No fix.

### H. AUTO-ECO wave-eco (a389dadc935, f89b41d158b, rt 08:35): 0 launches in 3.2 h.
- AUTO-ECO lines: 0. auto_resign.tsv last write 08:17. auto_resign_state.json has no item with source wave-eco.
- 130 jobs are DONE-NEAR-MISS, but 39 sit on terminated hosts (epyc4 17, epyc1 14, epyc5 7, epyc6 1) and 39 on the hub
  from old runs; 52 are on live hosts. Of the wave items, 133 are "SKIP already credited" and 14 are "WAIT probe: could
  not resolve hostname" for a terminated host. So the pass may be right that nothing is eligible. UNVERIFIED: it prints
  no reason.
- Structural fix: one line per pass: candidates N = credited a, DB host gone b, not plan-current c, submitted d. Jobs
  on a host outside derive_gen_hosts are retired, not probed each pass.
- Owner: WAVE-PILOT-FIX.

### I. Noise
- REAP-DEAD SILENT: 395 lines, all after 11:03 (73, 116, 96, 110 per tick): "unreadable: epyc7, probe-pending
  (reported only)". One summary line per host per tick would do. Owner: WAVE-PILOT-FIX.
- RESULT-RECLAIM "skip guard REFUSE: protected": 128 (246). The rail works; the sweep still asks.
- TOOL-SKEW UNMEASURED s81_head: 15 lines, fifth window. TOOLS-LAG: QC 1,414 commits, HBM 2,511, HEAD 407, S81 203,
  KV 156. SKEW (11:07): HBM trees differ from main in 263 of 263 closure modules (parked).
- ADOPT-GUARD PLAN_MISSING hbm on epyc2: 32 alert lines, same text each tick.
- failure_breakdown STALE: 109 (104 HBM parked, flat; KV 5, new: 4 superseded KV types 8-10 h old, 1 core unowned).
  Non-design classes in S81 types: "other flow error" 3 (was 152). NOT SEEN: intel2 epyc7.

### J. Admission, kills, disk
- Guard kills in the window: 0 on all 6 hosts (kills.log is UTC; last entries 02:46 PST, epyc7 04:29 PST).
- Admission refusals: UNMEASURED for the window (the last 4,000 admit lines hold epyc8 33, epyc2 26, epyc10 9,
  intel1 1, epyc9 1; I did not cut them by time). ot-run reserve is 0 on every host.
- Load at 11:47: epyc2 261/128, epyc8 140/96, epyc9 113/96, intel1 81/112, epyc10 68/96.
- Disk: epyc10 scratch2 93%, 582 GB free (685 at 07:45: about 25 GB/h down). epyc8 90%, 804 GB (975). intel1 83%.
  epyc2 scratch2 394 GB (148: recovered). Owner: FLEET-OPS-R.

## Did the fixes from FABLE-FLOW-0755 land?
- A snapshot copy (flock, timeout, INFRA): landed 1eccc0936b3. Works for new units (2 fails, both INFRA). 246 of 468
  live units still run older code; 88 old-form fails after the fix. Leftover copies not ended: epyc7 still at 1,074.
- B parallel ot-tools-sync: works. Every promotion since 08:20 has one line for each of the 6 hosts in the same second;
  5 hosts are on b098cf029b18. epyc7 fails each time and is 11 promotions behind. Retry of a missed host: not seen.
- D tar cross-device: landed 4578f44a345, did not work (30 of 30 lines still fail). Stop after 2: no.
- E KV bind retry key: landed 1d6dc572ff2. Works: 0 source-follow bind errors (24) and 0 "cached elaboration" lines
  (127). KV launched 3 (0); KV rows RUNNING 1, ENQUEUED 38 with 36 jobs running.
- F relaunch: partly. hd_spn_eshim_rx retry lines: 0 (252). REPEAT rose because of class A.
- H tick time: landed 432200e074b. Not enough: median 702 s, one tick 2,581 s.
- I epyc4: landed 79b848d74ef. Works: 0 host-key lines (74). CELL-BIG: 0 lines (1,620). auto_resign still probes
  terminated hosts (14 items).
