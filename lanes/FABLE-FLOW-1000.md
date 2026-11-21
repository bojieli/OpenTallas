# FABLE-FLOW-1000: procedural / flow review, window 11-21 07:47 to 10:02 PST

Lane FABLE-FLOW-1000 (Fable 5.2). Read-only review, process and tooling only. Nothing cancelled, signalled, launched or deleted.
Previous: lanes/FABLE-FLOW-0745.md (window 05:55 to 07:47). Fix lane since then: FLOW-OPS-0900.
Sources: autopilot/log.txt (479 lines in the window), autopilot/WATCHDOG.log, kit_wave_state.json, lanes/FLOW-HEALTH.tsv (09:28),
tools/failure_breakdown.py (run 09:46), `ot-run --status` (09:50), lanes/posts/*.md (369 posts in the window), LANE-STATUS.tsv,
hub and epyc10 systemd journals, ~/.local/state/disk-rate.log, epyc10 fam-qc-fefw/tmp watcher logs, rtx-pro ot-auto-export/rtx.log.
Marking: **V** = read or measured this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Fleet base: 235 running units (V, ot-run status 09:50), 2.25 h, so about 530 unit-hours in the window.

## Headline

1. **The autopilot tick hung for 50 min (08:47:57 to 09:37:56) and nothing noticed.** One tick sat in `poll_running`, used
   70 CPU-min, and was ended only by the 3000 s service timeout. No LAUNCH and no CLASSIFY for 52 min, then 13 launches
   by 10:00 (first at 09:56:49). First TICK-KILLED in the log. Class (a).
2. **Sender of the three slw_fe_v1 LEC kills found: the hub hung-job watchdog, rule SUPERSEDED.** It stops any scope whose
   `--dir` is the kit dir of a retired wave row, including a lane's LEC on a SIGNED kit. Posted to the lane at 09:52. Class (b).
3. **The epyc10 disk fall has a writer: private S81 source trees.** FAM-S81-SLICE-R4 broke hardlinks in place on two trees of
   54 GB each (08:46 to 09:20), on top of real-copy candidate trees; recovery was ot-delete of s81-j6 candidate trees at
   09:33 to 09:42. The cause is the same as the KV D26 drift: sealed trees can be written and linked. Class (c).
4. **A `git log --all -S ring_declared` has run on epyc7 since about 07:15 with no timeout**, holding 43.7 GB of deleted packs.
   The 09:30 alert named the pid; it was still alive at 10:02. Posted to FLEET-WATCH-R7. Class (g).
5. **Sign-off count: 494 any plan, 413 current plan (V 09:46), +0 / +3.** 6 SIGNED classified in the window. The rtx-pro exporter was in DISK HOLD from 04:20 to about 09:35 (310 hold lines, 16 units).
6. **Wave: 12 launches, 5 FAIL lines (3 src_manifest, 2 place), 0 gen failures** in 07:47 to 09:45. STALE 106 (104 HBM parked, 1 KV, 1 QC).
7. **Lane turnover: 22 stand-downs in 2 h** (17 in the last window); 4 are finished review lanes, 9 name context.

## FLOW-OPS-0900 fixes: did the class stop

rt/current is d032c7204022 on epyc10 (V 09:55).

| Fix | State this round |
|---|---|
| a7e43f05a7 struct-carry | Live (V): `LAUNCH-HELD STRUCT-CARRIED` on qwen_compute/slw_fe_v2 at 08:45. **Not closed for KV pv**: the 11 old stops stay block-keyed until the PV lane re-runs `struct-stop`; kv3_pv_v5, v7, v12 launched 07:55, and kv3_pv_v8 launched again on KV-D26 at 09:57 after failing at place at 08:15 (V). |
| dd507bc8ba CELL-CAP report | On main 09:28. Not exercised: no gen ran between 09:28 and 09:56. |
| 0db164c936 UNSIGNABLE acts | Works (V): 5 NOTICE, 2 DECISION, 1 cancel (09:01, lepe_mu_LP t2 -891 ps, 4.8 h, evidence row written). No KEEP post in the window. The cancel line reads `epyc10: ot-heavy-stop: 0 scope(s) stopped` for a job listed on epyc9: check that the unit really ended. |
| ff9ae75e61 drain refusal | Works (V): `DRAINING (131 of 250 GB, new job dirs refused)` on intel1 and epyc9. intel1 scratch 98 GB (08:05) to 133 (09:35). |
| 8da9e6e4c2 ARGV-GUARD | No fan-out death in the window. DIED posts under 120 s: 20 of 49 (was 42 of 85). |
| 9c08762d8b cause in fail key | Landed 09:00, after the 3 src_manifest FAIL lines, which still read `UNCLASSIFIED[design:src_manifest] ... and 76 more`. Recheck next round; a manifest drift should class as FLOW/src with the first path, not `design`. |
| 951f711715 relay handover | Works (V): class 1944890cf7 went KV-PLAN-R5 to KV-PLAN-R6 with one HANDOVER post and one NEEDS-LANE. Open 49 min. |
| a79be6d0fd / 8bce6e7c35 count by manifest, tag at adoption | Count before = after at 09:21 (R). Auto tags now wait for a released canary, and no canary has run since 11-04: no tag will be cut. Class (f). |
| 204670a997 private-spec fail closed | Used by FAM-QC-COLL-R2 (R). No false refusal seen. |
| ac0f9ac2f6 delete manifests | Live (V): 8 manifests on epyc10 09:33 to 09:42. Record only; see class (h). |
| f77c697efa delta-apply real copy | Live. Side effect: every private tree outside the base dir is now a real 54 GB copy. Class (c). |
| 3ed87c352a PLACE-SETUP-STOP measure | On main 09:31. Two wave rows capped on this stop launched again at 09:58 (V: slice_station t45, slw_st_a_v2 clf4365a62; reason not read). Private and running kits keep the old tcl. Class (e). |

Guards that worked (V): SKIP-SAME-INPUT 4, STRUCT-CARRIED 1, CAUSE-CAP 2, BLOCKED-CAP 2, HOLD-AUDIT 0 on all counters (8 ticks),
DISK-RATE once per state with lsof holders, 5 GRT-ARM STRUCT-STOP cancels (3.3 to 6.4 h jobs).

## Classes, ranked

### (a) Control loop outage: one hung tick stops the whole wave (NEW, largest)

- Count (V): 1 event, 50 min 20 s. Journal: `autopilot.service: start operation timed out. Terminating ... Consumed 1h 10min 48s
  CPU time over 50min 20s wall clock`. Last line of the tick: POLL-TIMES at 08:48:21. Next tick 09:39:56 printed
  `TICK-KILLED previous tick started 08:47:57 was cut off in phase 'poll_running' after 24 s`. Log lines per 10 min: 80 at
  08:30, 2 at 08:50, 3 at 09:00 (only the aux timer wrote). Ticks today: 60, mean 383 s, max 751 s.
- Effects (V): PROGRESS-WATCH NO-PROGRESS on s81 (120 min), s81_head (122 min), qwen_compute (68 min). Results that ended
  in the gap were classified from 09:40 on (at least 2 SIGNED, 1 CRASH, 1 CANCELLED). The only wave lines in the gap are two
  GRT-ARM cancels at 09:15 and 09:16 (writer not identified: the hung tick or a timer); their slots were not refilled.
- Trend: first of its kind in the log. The cause is unknown: the process left no stack. CPU above wall time points to a
  busy loop with threads, not a blocked ssh (I).
- Root cause (V): `TimeoutStartSec=3000` on a tick that never needs more than 751 s. No per-phase deadline. No stack dump on
  SIGTERM. PROGRESS-WATCH alerts per die on launches, so three alerts said "no launch" and none said "the tick is dead".
- Structural fix (P): (1) TimeoutStartSec 900. (2) `faulthandler.register(SIGTERM, all_threads=True)` plus
  `dump_traceback_later(600)` into autopilot/tick_stack.log, so the next hang names its line. (3) Each phase gets a wall
  budget (poll_running 300 s); over budget it logs PHASE-OVERRUN, skips to the launch pass, and the tick ends normally.
  (4) stall-watch posts one ALERT TICK-DEAD when log.txt has no `TICK-TIMES` line for 20 min.
- Owner: KIT-OPS-5 (1 to 3), FLOW-HEALTH-1 (4).
- Fleet time: about 1 percent of compute (I: threads stayed 100 percent booked; freed slots idle up to 50 min). The cost
  is 40 percent of the window with no launch or classify decision.

### (b) Hub watchdog rule SUPERSEDED kills lane jobs that run in a retired row's kit dir

- Count (V): 3 in the window, all the same job: FAM-QC-FEFW-R2 routed LEC of slw_fe_v1__clfe325744__cldb4efe33 (SIGNED 08:15).
  WATCHDOG.log lines 2325, 2327, 2329: `STOP epyc10 oth-ubuntu-1841527 / -2391296 / -2711285 ... why SUPERSEDED: row
  s29q103S4Q9N46C@1 CANCELLED class SUPERSEDED: retired; event is not current`. watchdog.service ended 08:35:08, 08:55:40,
  09:14:40; the three DIED posts end at 16:35:08, 16:55:40, 17:14:40 UTC. epyc10 journal: scope `Stopping` at 08:34:46,
  08:55:04, 09:14:18. No OOM line. Rule SUPERSEDED stops per day: 33 (11-18), 1, 11, 3.
- Trend: the rule is old. The victim type is new: lanes now run LEC, ECO and re-sign jobs inside wave kit dirs of old
  events, because any-plan sign-off counts.
- Root cause (V): the rule matches a scope by its `--dir`, not by the unit the wave launched for that row. It runs from the
  hub with no post and no OT_LANE lookup (`lane ?`), so the lane saw rc 143 "from the docker shim" and spent 80 min and
  three runs building watchers on the wrong host. 0745 item (h) "4 rc 143 bind jobs, no post names the stopper" is the same gap.
- Structural fix (P): (1) the rule stops only unit names recorded on the row (`kw-*`, `ap-*`), never an `oth-*` unit of
  another owner; a row whose result is SIGNED is skipped. (2) Every stop by any tool goes through `ot-run --cancel`, which
  already writes signals.log and the DIED post; the post gets `stopped by <tool>: <rule>`. A stop with no named sender
  cannot happen.
- Owner: FLOW-HEALTH-1. Now: FAM-QC-FEFW-R2 runs the LEC with a `--dir` outside the wave kit, or lists the kit in WATCHDOG.skip.
- Fleet time: 0.5 unit-hours, 0.1 percent. The cost is 1.5 h on a sign-off proof and one lane's context.

### (c) Sealed source trees can be written and linked: KV D26 drift, and the epyc10 disk fall

- Count (V, R): (1) FAM-KV-HUBC-SYSC swapped 6 view dirs inside the sealed KV D26 tree on 6 hosts; 3 wave FAIL lines
  (kv3_hg_v1p4 twice, v1p3), src breaker opened, reverted 09:19. (2) epyc8: 3,047 files of the D26 tree have nlink 2 from a
  `cp -al` made at 00:26 by an unknown lane; `--ro` verify fails there; KV hosts cut to epyc7 and epyc10 at 09:41. (3)
  FAM-QC-COLL private kit died at src_manifest on a hardlinked tree. (4) FAM-S81-SLICE-R4 broke hardlinks in place on
  src_s81_j6r1_t37fstart and src_s81_j6r1_l6: 328,082 files and 54 GB each (V: du 54 GB; unlink.log 08:46 to 08:58,
  unlink2.log 08:59 to 09:20). (5) s81-j6 holds 27 cand* dirs on epyc10 (sizes not measured); 6 trees of about 300k files each were ot-deleted there
  09:33 to 09:42 (V delete manifests, size I).
- epyc10 scratch2 (R FLEET-WATCH-R7, V disk-rate.log): 424 GB at 08:01, 312 at 08:48, 218 at 09:06, low 153, then 213 at
  09:28; 206 GB and 98 percent used at 09:55 (V). 108 GB of the 159 GB fall after 08:48 is item (4) (I). The watch looked
  at ot-jobs dirs and deleted-open files; lane tree dirs were outside its sample.
- Trend: third form of one cause since 11-15 (SRC-TREE-1115). f77c697efa closed the hardlink route by making real copies,
  which moved the cost to disk: one S81 private tree is 54 GB.
- Root cause (V): `publish` makes a tree `chmod a-w`, which the owning uid can undo, and a hardlink to a read-only file is
  still allowed. So the seal is a convention. Lanes need a cheap private tree per candidate and have two choices: links
  (drift) or copies (disk).
- Structural fix (P): (1) `publish` ends with `sudo chattr -R +i` on a tree of record. Rename, write, chmod and `ln` then
  fail with EPERM for every uid, so (1) and (2) cannot happen; ot-delete and auto-retire clear the flag under the guard.
  (2) Private trees become overlays: private-spec takes `--base <sealed tree> --delta <dir>` and the kit reads base plus
  delta, so a candidate costs its changed files (MB), not 54 GB. (3) `src_manifest.py links` on a SHARED-INODE error prints
  the other path; run it once on epyc8 to find and unshare the 00:26 copy, then put epyc8 back. (4) disk_rate.py at state 2
  adds the top 5 lane dirs by growth (du delta of claude/*, cached), not only ot-jobs.
- Owner: KIT-OPS-5 (1, 2), FLEET-WATCH-R7 (3, 4), CLEAN-ALL-1115 (candidate tree retire rule: gate FAIL or superseded
  candidate, older than 6 h).
- Fleet time: about 1 percent (I: 4 kit attempts lost early, KV on 2 of 3 hosts, epyc10 admission held, see d).

### (d) A host pin plus the disk-ETA hold queues small jobs behind a full disk

- Count (V, R): 4 lanes in the window: FAM-S81-LEPE-3 proof10 (client looped in HOLD on epyc10 with no unit; moved by hand
  to epyc7, admitted in 1 s), FAM-S81-COL-H9R0-R2 (epyc8 hold, went to epyc10), FAM-QC-COLL-R2 (tree recompose held on
  epyc10), FAM-S81-MISC-R3. epyc7 had 429 to 529 GB free the whole time.
- Root cause (V): lanes pin `--hosts` to where the tree is. The disk-ETA hold is a wait with no end and no unit, so
  `ot-run --cancel` has nothing to cancel and the lane kills its own client pid. ot-run has AUTOSTAGE (signals.log shows it
  moving dirs epyc10 to epyc7) but does not use it for an ETA hold.
- Structural fix (P): in an ETA hold of more than 10 min, a job with `--stage` paths or a `--dir` under 20 GB is staged to
  the listed host with the most free disk and runs there (same path, the existing AUTOSTAGE). Other jobs exit 75 NOT-RUN
  with the host list. No rail changes: the hold stays for jobs that would write to the full disk.
- Owner: KIT-OPS-5. Fleet time: under 0.5 percent; 20 to 60 min of latency per proof kit.

### (e) A tool fix does not reach kits that are already generated

- Count (R FLOW-PLACEMEAS-1121): 64 PLACE-SETUP-STOP jobs in the census, class fclk landing or reset recovery; three
  re-measured examples move by 20 to 230 ps and two flip from stop to pass. Wave state (V): 8 rows BLOCKED-CAP on this
  stop. The wave re-arms failed rows on an rt change (KW_REARM 31 KV rows at 08:44, `rt_tools=17`); two rows capped on this
  stop launched at 09:58 (reason not read).
- Root cause (V): gen copies flow tcl into the kit. A re-arm repeats gen and place (1 to 3 h) to redo a 2 min STA measurement on a
  placed DB that still exists. Private kits and running kits have no re-arm at all.
- Structural fix (P): (1) kits read measurement tcl (postplace, tt_setup, signoff reports: no layout effect) from the rt
  snapshot named in kit_effective_env, not from a copy; layout tcl stays copied. (2) `kit_wave.py remeasure --stop
  PLACE-SETUP-STOP` runs the new measurement on the kept 3_place DB and rewrites the verdict; only rows that still stop keep
  the cap. (3) A stop verdict stores the sha of the tcl that produced it; a different sha on main marks it STALE-VERDICT in
  failure_breakdown.
- Owner: KIT-OPS-5. Fleet time: about 2 percent ahead if the 64 are re-run from gen instead of re-measured (I).

### (f) Flow canary dead since 11-04: tags cannot be cut, signed results are signed twice

- Count (V, R): canary runs root exists on no host. 8bce6e7c35 makes the auto tag wait for a canary RELEASE, so every die
  pin newer than the last hand tag yields SIGNED-UNVERSIONED. failure_breakdown: 3 QC types "signed (count pending)".
  AUTO-RESIGN ran slice_station t43 on a 4-day-old tag at 08:38.
- Structural fix (P): the canary is a wave row (`kind canary`, one small signed type per die, priority die) launched by
  pin_tags_step when the flow manifest has no tag; its SIGNED result cuts the tag. No separate service to die.
- Owner: FLOW-CANARY-1121 (started 09:5x, first push 09:58). Fleet time: about 0.5 percent (re-sign runs).

### (g) Git history search without a timeout, again

- Count (V): 1. epyc7 pid 2832979 `git log --all --oneline -S ring_declared`, cwd fable-die-head/repo, parent bash, no
  OT_LANE, 2 h 46 min old at 10:02, so started near 07:15, six minutes after the rule was posted. 43.7 GB held.
- What worked: the new lsof line in DISK-RATE named pid and command at 09:30. What did not: the alert went to FLEET-OPS-R as
  text; no lane owns "act on a named holder", and the process has no lane.
- Structural fix (P): the 0745 shim (history searches under `timeout 600` when stdin is not a terminal), on every lane
  PATH. disk_rate.py: a holder that is a git history search older than 10 min is posted as NEEDS-ACTION to FLEET-WATCH
  with the exact pid, not as a suffix of a rate line.
- Owner: FLOW-HEALTH-1 (shim), FLEET-WATCH-R7 (stop the pid after a cmdline check). Fleet time: none yet.

### (h) Idle-tree retire deletes inputs that exist nowhere else

- Count (R FLEET-WATCH-R7, 08:42): 1 found. ot-auto-retire on epyc2, 11-18 03:56, deleted fable-pd-head-clk (idle 76.5 h,
  disk at 709 GB free, no pressure) with ring_declared.json, a generated input that was never committed. Found 3 days
  later through a failed HEAD step.
- Root cause (V): the guard protects what kit_wave.json, the signed store and PROTECTED-DBS name. A lane file that a later
  plan step reads is in none of them. ac0f9ac2f6 records path and sha; the bytes are still gone.
- Structural fix (P): before a lane tree is removed, retire packs every file under 50 MB that is not a tool output
  (json, tsv, tcl, sdc, py, sv, md, sh; not odb, def, spef, gds, log) into `<archive>/retired/<host>/<tree>.tar.zst` and
  names the tarball in the delete manifest. A few MB per tree; no small input can be lost. No pressure, no retire: the
  idle-tree pass runs only when the disk is in drain state.
- Owner: CLEAN-ALL-1115. Fleet time: none; one HEAD plan step blocked.

### (i) Lane turnover and waiters

- Count (V): 22 stand-downs 07:47 to 09:45 (S81 9, KV 5, QC 3, HEAD 2, flow and closure review 3); 9 name context, 3 give
  a number (282k, 304k, 318k). Measured lifetimes of successors that already stood down: 0.73 h, 0.82 h, 0.88 h, 2.1 h, 3.2 h.
  Job-end posts: 91 DONE, 49 DIED (22 rc 1, 6 rc 143, 5 rc 4). Waiter processes: 159 on rtx-pro (77 older than 2 h), 74 on the hub.
- Not measurable (V): ot-wait keeps no ledger, so timeouts and wake-ups without a result cannot be counted. The brief's
  "false wake-ups" stay R.
- Root cause (I): a lane is woken once per job end, reads raw client logs to decide, and a successor re-reads the handoff
  and re-arms every waiter. Three lanes used a third of their life on a kill with no named sender (class b).
- Structural fix (P): (1) ot-wait appends one line per exit to lanes/WAITS.tsv (lane, unit, rc, waited s, timeout yes/no);
  next review measures this class. (2) `ot-wait --digest`: one waiter for N units that returns once, when all ended or the
  first failed, with a 10-line verdict per unit (stage, WNS, DRC, first error line). (3) Waiters belong to the unit, not the
  lane: the DONE/DIED post already lands in the successor file, so a successor reads posts and re-arms nothing.
  (4) stand-down.sh refuses under 60 min of life unless `--why` is given, and prints the lane's lifetime in the row.
- Owner: new (continue FLOW-PROC-B). Fleet time: about 0 percent of compute; the largest cost in lane hours.

### (j) Carried

- Exporter (V): rtx-pro root 96 percent, 150 GB free, reserve 100. DISK HOLD 04:20 to 09:35; exports resumed 09:40. It will
  hold again within hours. Owner decision on afg, .cache, closed_archive is open (R FAM-QC-FEFW-R2). CLEAN-ALL-1115.
- `route_hold:WAIT-FORM=53`, fifth review. `SKIP-HELD=62`, `KW-FIX-45=8`. s81: 319 rows on the J6 hold, 27 eligible rows,
  0 launches for 120 min. s81_head: 17 eligible rows, 0 launches for 122 min, no NO-LAUNCH line says why.
- HBM is parked and still prints 2 ADOPT-GUARD alerts and 2 bind-preflight lines per tick, and TOOL-SKEW 278 of 278. KIT-OPS-5: `parked` flag.
- TOOLS-LAG: QC 208 commits, HEAD 154, both missing r708 (0745: 195 and 141). MERGE-QUEUE-1.
- Skew (V FLOW-HEALTH 09:07): cross-host compare ok on 6 trees; s81 tree on epyc7 `manifest rc=124` (timeout, not a result).
- KV core qkd_pv_fin_s8_pin CANCELLED 24.3 h, unowned, fifth review. COORD.
- AUTO-ECO: 31 candidates "probe skipped: ssh failed" and 5 "could not resolve host" on every aux tick for the whole window.
- ot-run end times from epyc hosts are still UTC under a PST label.

## Do now (ordered)

1. KIT-OPS-5: tick timeout 900 s, stack dump on SIGTERM, phase budgets; FLOW-HEALTH-1: TICK-DEAD alert (class a).
2. FLOW-HEALTH-1: watchdog SUPERSEDED rule stops only the row's own units and skips SIGNED rows; every stop names its sender (class b).
3. KIT-OPS-5: `chattr +i` at publish and overlay private trees; FLEET-WATCH-R7: find the epyc8 hardlink copy, lane dirs in the disk alert (class c).
4. FLEET-WATCH-R7: stop epyc7 pid 2832979 after a cmdline check; FLOW-HEALTH-1: the git shim (class g).
5. KIT-OPS-5: AUTOSTAGE on a disk-ETA hold (class d); measurement tcl from rt and `remeasure` (class e); KV pv struct-stop by type (0745 a, still open).
6. FLOW-CANARY-1121: canary as a wave row that cuts the tag (class f).
7. CLEAN-ALL-1115: small-file tarball before retire, retire only in drain state (class h); rtx-pro root (class j).
8. New lane: WAITS.tsv ledger and `ot-wait --digest` (class i).
