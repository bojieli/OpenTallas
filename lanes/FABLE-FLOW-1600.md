# FABLE-FLOW-1600: procedural / flow review, window 11-20 13:55 to 15:51 PST

Lane FABLE-FLOW-1600 (Fable 5.2). Read-only review, flow only. Previous: lanes/FABLE-FLOW-1400.md.
Sources: autopilot/log.txt (1,322 lines from 13:40), ot-run --status and ot-heavy-reconcile --free on the 6 build hosts
(15:45, 15:50), tools/failure_breakdown.py (15:46), process tables on 6 build hosts + localhost, docker ps on epyc7,
lane posts, intel2 /tmp/push-*.log, lanes/FLOW-HEALTH.tsv (15:08).

## Headline

1. epyc7 starts containers again (since about 15:28, dockerd not restarted). The reconcile with timeouts is installed on
   all 6 build hosts (same file, 15:47). The watchdog now sees containers on epyc8, epyc9, epyc10 (39, 50, 44).
2. Placement is still wrong after the fix. At 15:50 five hosts admit 0 GB with 183 waiters asking for 6.3 TB; epyc7
   admits 150 GB and has 0 waiters. S81 cannot use epyc7, and lane jobs started with ot-run --dir cannot move at all.
3. The auto-visual reviewer is NOT on main. Its push failed at 15:01 (a sparse-clone test artefact) and nobody noticed:
   the last ROUTE-RELEASE-1300 post (14:50) says "push running". WAIT-VISUAL went from 34 (14:59) to 64 (15:51).
4. Waiting by pgrep is a fleet-wide habit, not one accident: 181 waiter shells on 6 build hosts + localhost match only
   themselves; 168 are older than one day. Each is a job whose end nobody was told about.
5. Launches: 181 (hour 13, the J5 apply), 36 (hour 14), 31 (hour 15 to :51). The fall is mostly five memory-full hosts,
   not epyc7 alone: all 624 threads are used and load is 1.3 to 3.7 x cores.

## What 14:00 asked for and what happened

| 14:00 item | state at 15:51 |
|---|---|
| Watchdog blind on epyc8/9/10 | fixed: scans list 39 / 50 / 44 containers |
| HUNG-WATCH cancels admission waiters | 5 cancels (was 16); not fixed in code, see class 4 |
| Cancel classed as OOM (marker) | not seen landed; 2 hub lines with Error 241/247 in the window |
| Host OOM kills | not measured: the earlyoom journal is not readable from this user; hub shows 2 kill lines |
| J5 tree on epyc7 + gen_hosts | tree is there (55 GB); no verified receipt, s81 gen_hosts still without epyc7 |
| RESUME-MOVE source host | 1 more failure, same cause (13:40, rc 11) |
| Mechanical route release in the autopilot | written, push failed, not landed (class 3) |
| Proofs with priority | done by hand at 15:2x: t60 and cbf run on epyc7 (t60 container up since 15:37) |
| Unchanged design retries | REPEAT-STOP landed 6ea719be97; 3 LAUNCH-HELD at 15:17 |
| J5 pins, post-apply bind, t7 priority | not re-checked here (die owner scope) |

## Classes

### 1. A host that admits but cannot start (epyc7)

- Count, trend: 1 event. Last container 14:30, none until 15:2x (1 at 15:20 to 15:29, 11 at 15:30 to 15:39). About 55 min.
- Root cause: ot-heavy-reconcile called docker inspect with no timeout; 9 containers with dead cgroups made it hang;
  sweep and reaper scans piled 20 more hung clients. Admission kept advertising 128 GB.
- The second half of the cause is still open: the hub believed the number. RESTAGE moved 30 waiters to epyc7 between
  14:40 and 15:29 (8, 5, 5, 6, 6 per 10 min), into a host that could start nothing.
- Structural fix: admission is proven, not computed. A host reports admit 0 unless a no-op container started under a
  timeout in the last 10 min (the reconcile writes last_start_ok). The hub posts once when a host admits over 32 GB, the
  fleet has waiters, and that host created no container for 15 min.
- Owner: FLEET-WATCH-1400 (timeouts done; start canary and hub line open).
- Fleet time: epyc7 had 367 to 397 GB available of about 6 TB, so about 6 percent of fleet memory for 55 min, plus 30
  moved rows delayed up to 50 min.

### 2. Waiters stay on full hosts while another host has room

- Count, trend: 15:45 and 15:50: epyc2 0 GB / 38 to 41 waiters, intel1 0 / 49 to 51, epyc8 0 / 31 to 32 (1,990 GB asked,
  62 GB each), epyc9 0 / 29 to 33, epyc10 0 / 29 to 34; epyc7 admits 135 to 150 GB, 0 waiters. Same picture as 13:43.
- Should waiters move automatically: yes, and the mechanism already exists in two halves. Neither half is complete.
  - ot-run REBALANCE (300 s requeue) only moves between hosts that already hold --dir. Lane jobs (proofs, bisects) are
    therefore pinned: proof/t60 and proof/cbf sat about 2 h behind 33 waiters (1.2 TB) on epyc10 until a lane copied them
    by hand; the FLOW-NOADV-R2 t10 bisect is still queued on epyc9.
  - Autopilot RESTAGE works (73 moves in the window, all to epyc7) but runs once per tick (264 to 717 s) and only for
    dies whose gen_hosts include the target. s81 gen_hosts are epyc8, epyc2, epyc9, epyc10, intel1. 29 GEN-HOST-TREE and
    42 RETRY-HOST lines read "gen host epyc7 -> <full host>". The J5 tree is now on epyc7 but HOST-RECEIPT-MISS (15:24,
    15:31) keeps it out: copied, never verified.
- Structural fix:
  - ot-run: when a waiter is not admitted after REQUEUE_S and another host admits the request, ot-run copies the declared
    inputs (--stage paths, or the sealed job spec) to that host and requeues there. Data locality becomes a cost, not a
    limit. A request with no declared inputs prints "PINNED: no --stage" at submit, so the lane knows at once.
  - Plan apply: a die tree is synced and receipt-verified on every gen host as part of the apply; derive_gen_hosts fails
    loudly when a host that admits over 100 GB is missing the tree of the die with the most waiters.
- Owner: FLEET-WATCH-1400.
- Fleet time: 135 to 150 GB admit idle, about 2.5 percent of fleet memory, continuous since 13:43 (3 to 4 jobs of 32 to
  62 GB at any moment). Lane time is the larger loss: about 2 h on each of two proofs.

### 3. Jobs that die without anyone noticing

- Count, trend: 181 pgrep-style waiter shells whose pattern matches no process except shells that carry the pattern in
  their own command line: epyc7 46, epyc9 23, intel1 21, epyc2 16, epyc8 11, epyc10 5, localhost 59. Age: 13 under a day,
  93 between 1 and 7 days, 75 over 7 days. 6 waiters have a live target. intel2 not scanned.
  Limit of the check: for localhost waiters that run pgrep over ssh, I tested the pattern locally; the remote shell
  carries the pattern too, so the result holds, but those rows were not tested on the remote host.
- Cases in this window:
  - lepe proof7: died 11-19 23:55, noticed after 16 h.
  - ROUTE-RELEASE-1300 push: "TESTS FAILED rc=1; nothing pushed" at 15:01
    (test_kit_wave_kit_rtl_post::test_script_mode_uses_the_same_step, FileNotFoundError on
    physical/die_plan/s81/kit_wave/kit_rtl.sh, which is outside the lane clone's sparse cone). No post after 14:50, no
    push process on intel2 at 15:50. rt/current (ec16babe0dfb) has no auto_visual file; the log has 0 AUTO-VISUAL lines.
  - A waiter on epyc7 for "ot-push-main --test-timeout 1500" is 88 min old with no target.
- Root cause: the waiter asks "does a process with this text exist" instead of "what was the exit status". The question
  is true of the waiter itself, and a job that died and a job that passed look the same.
- Structural fix: one standard waiter, and the job reports its own end.
  - ot-run and ot-push-main write <dir>/.ot-exit (rc, end time, last log line) from an EXIT trap and call post.sh
    themselves with DONE rc=N or DIED. A lane then needs no waiter for the two most common cases.
  - ot-wait <unit or pidfile>: waits on the systemd unit or on the exact PID with its start time, then prints the rc
    from .ot-exit; "unit gone and no .ot-exit" prints DIED and exits non-zero. No pattern matching anywhere.
  - rules.txt: "never wait with pgrep; use ot-wait". The reaper lists waiter shells that match only themselves for
    over 1 h and posts them once (report only).
- Owner: new (WAITER-STD-1600), with FLEET-WATCH-1400 for the ot-run part.
- Fleet time: compute near 0. Lane time: 16 h on the lepe critical path; 50 min and counting on the route release, which
  holds 64 placed kits.

### 4. HUNG-WATCH cancels rows with no container

- Count, trend: 5 cancels (13:46, 14:07 x2, 15:22 x2), was 16 in the previous window. All "containers none", CPU 37 to
  468 s, 35 to 47 min. One correct no-cancel (c1x_C__t5, CPU busy).
- At least 3 of the 5 (sle_fe_v1__cl8210183c, slw_hc0__cl4f54b7a3, cbf_q01_s2) are rows whose epyc7 containers were among
  the 9 with dead cgroups, so for them the cancel was right and the cause was class 1. The other 2 were not checked.
- Root cause and fix: as 14:00 class 4 (a row waiting for admission is not judged; use hung_watch_min). Not landed.
- Owner: FLEET-WATCH-1400. Fleet time: under 1 percent.

### 5. WAIT-VISUAL with no reviewer

- Count, trend: 34 (14:59), 36, 46, 47, 54, 60 (15:43), 64 (15:51): about 35 per hour. WAIT-FORM 40, flat.
- Root cause: class 3. The by-hand pass at 14:09 released 30; the code that would repeat it each tick did not land.
- Structural fix: land it from a full clone, or make the test skip with a reason when its file is outside the cone.
- Owner: ROUTE-RELEASE-1300. Fleet time: 0 compute; 64 placed kits wait at route, the rows nearest to sign-off.

### 6. Unchanged retries and misread failures

- Count, trend: FAIL lines 14 (13:45 to 13:59), 10 (hour 14), 8 (hour 15). REPEAT-STOP works after 6ea719be97: 3 rows
  LAUNCH-HELD at 15:17, 21 SKIP-SAME-INPUT lines.
- Left over: (a) one class on several types is not seen as one class. MPL-0020 at macro_place hit 4 S81 svc_hi types
  (14:47, 15:03, 15:29, 15:37), each counted alone. (b) kv3_pc_v1 has two forms with separate streaks (15:37 fail on the
  second form). (c) the FAIL reason is an info line: ot_s81sl_leaf__t7 and ot_s81sl_kv_leaf__t1 failed at gen at 13:57
  and the recorded reason is "TAP-LIMIT-INFO ... (info: not blocking)", class INFRA. t7 is the row the 74 leaf holds wait
  for; its real gen error is not in the log line.
- Structural fix: the reason extractor skips lines marked info / not blocking and takes the last ERROR; when one
  fingerprint reaches 3 types of one family in an event, the autopilot posts one CLASS line to the die owner (a post,
  not a hold).
- Owner: FLOW-NOADV-R2. Fleet time: under 0.5 percent (all fail at gen or early place).

### 7. Push gate

- Count: intel2 /tmp push logs hold 8 PUSHED and 3 TESTS FAILED. In the window: ROUTE-RELEASE-1300 failed (15:01),
  FABLE-FIX-KV-PV-R2 failed 14:19 then pushed 15:10. I found no timeout line in these logs; the 900 s limit is the
  ot-push-main default (--test-timeout 900) and the gate takes about 35 min, so lanes pass 1500 or 2400 by hand.
- Root cause: the default is below the measured run time, and the test set assumes a full checkout.
- Structural fix: default timeout from the measured p95 of the selected tests; tests that need a path outside the clone
  skip with a reason; ot-push-main posts PUSHED or FAILED itself (class 3).
- Owner: FLOW-NOADV-R2. Fleet time: lane time only, 35 min per attempt.

### 8. Skew checks that measure nothing

- TOOL-SKEW UNMEASURED for qwen_kvsys and s81_head (pin manifest missing on the hub); TOOLS-LAG s81 unmeasured (bad
  revision 'j5tree..main'). Three of five dies have no tool or src skew reading. WARN: s81 489 of 18,020 modules differ
  from the pin, qwen_compute 485 of 17,987, 7 times an hour, unchanged. No SRC-INCOMPLETE line since 13:20.
- Structural fix: the manifest is written when the pin is made (a pin without one is refused at edit time);
  UNMEASURED becomes a FLOW-HEALTH row with an owner.
- Owner: FLOW-NOADV-R2. Fleet time: 0; risk only.

### 9. STALE and non-design classes (failure_breakdown 15:46)

- STALE 105: HBM 104 (parked: 42 lint advisory, 51 cancelled superseded, 6 no row, 5 route-held since 11-13) and KV 1
  (core qkd_pv_fin_s8_pin, cancelled superseded 09:28, unowned).
- Non-design rows: kit input missing 1 (kv3_hub_C, failed 14:07 and 14:47), bind stale 1 (kv3_pv_v8), cancelled
  superseded 2. Count line: signed any plan 474, current plan 409.
- Owner: KV-PLAN-R1 for the 3 KV rows. No fleet time.

### 10. Disk and admission refusals

- Disk: no refusal in the window. Free: epyc8 scratch 93 percent used, intel1 scratch2 92, epyc9 89, epyc10 88, epyc2
  root 85. 14 delete-guard refusals on RESULT-RECLAIM, all protected trees (intended).
- Admission: 1 "NOT RUN: admission lock busy within 3600 s" (epyc8, 14:45): a request dropped after one hour waiting
  for the lock, not for memory. epyc8 runs 547 threads on 96 cores (load 349 to 363) and still charges peak 0.
- Structural fix: the lock holder is bounded by the new timeouts; confirm on epyc8 that no hold exceeds 60 s, and have
  NOT RUN name the holder PID.
- Owner: FLEET-WATCH-1400. Fleet time: 1 job.

## Do now (ordered)

1. ROUTE-RELEASE-1300: push the auto-visual reviewer again from a full clone. 64 placed kits wait on it.
2. FLEET-WATCH-1400: verify the J5 tree on epyc7 (receipt), add epyc7 to s81 gen_hosts. Then the start canary.
3. FLEET-WATCH-1400: ot-run requeue that stages inputs to the admitting host.
4. New lane WAITER-STD-1600: .ot-exit + self-post in ot-run and ot-push-main, ot-wait, the rule line.
5. FLOW-NOADV-R2: reason extractor (t7 real gen error first), CLASS post, push timeout default, manifest at pin.

Not checked: OOM kills (journal not readable); how epyc7 recovered (no post, dockerd start time unchanged); the 2
HUNG-WATCH cancels outside epyc7; whether the 13 young waiter shells have remote targets; intel2 waiter shells;
J5 bind, tool pins and the t7 hold (die owner scope); wait time per waiter (ot-run reports counts, not ages).
