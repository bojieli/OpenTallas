# FABLE-FLOW-0500: procedural and flow failures, 01:43-03:50 PST

Reviewer: FABLE-FLOW-0500 (Fable). Read-only. Measured 2026-11-17 03:43-03:52 PST on hub intel2.
Sources: autopilot/log.txt 01:43-03:43 (2,852 lines, 25 ticks; 0300 window: 8,226 lines), lanes/FLOW-HEALTH.tsv
(written 03:07), tools/failure_breakdown.py (03:45), `ot-run --status` (03:46), df/load/PATH/md5 on 6 build hosts
and the hub (03:45), merge-queue and git-mirror journals, rt/history.log, lanes/posts since 01:45.
Previous: FABLE-FLOW-0300. Scope: process and tooling only. Clock: all times are hub PST; COORD's event times
("02:50", "0300", "0500") run about 60-70 min ahead of these stamps.

## Headline

1. The approved fixes all merged, but none was live before 03:01. rt/current stayed on c3d5cd1ec83d from 01:03 to
   03:01 (118 min): 9 of 9 tools syncs in 01:51-02:31 ended SMOKE-FAIL (tools/autopilot/test_kit_wave.py Step
   tests, a different subset each time). The failures start and stop with the hub disk-floor hold (below). So the
   disk fixes could not deploy because the disk was low. Every "did the class drop" answer below rests on
   45 minutes of live time (03:01-03:46), not 2 hours.
2. The wave launched nothing for 105 min: KIT-WAVE HUB-DISK refused launches from 01:13:52 (hub scratch2 45 GB
   < 64) to 02:58:58. The line was logged once at the start. 23 rows were enqueued in that time and 22 launched
   at 03:00-03:23. No ALERT, no post, no actor until the disk was cleared by hand.
3. r531 and r533 are merged but not installed. `ot-delete` and `ot-gate-remote` are on PATH on 0 of 8 hosts
   (6 build hosts, hub, localhost), while the localhost raw-rm hook is installed and points lanes at them.
   /usr/local/bin/ot-heavy differs from rt/current on 7 of 7 hosts (19 lines on intel1; the installed file has
   no THREAD_MEASURED_FACTOR).
4. Fleet use is flat: median 43% of 624 threads over 25 ticks (range 35-56%; 0300: 41%). Load now: intel1 45/112,
   epyc2 28/128, epyc7 42/96, epyc8 51/96, epyc9 72/96, epyc10 70/96 = 309/624 (50% at 03:45, 46% on the 5-min
   figure). epyc10 is REFUSED for all new jobs (scratch 45 GB < 50).

## Which approved fixes are live, and did the class drop

All are on main and in rt/current (0840db8cbfe6 at 03:31, acfed0c60a55 at 03:46).

| Fix | Merged (PST) | Live | Class dropped? |
|---|---|---|---|
| r524 stage-ODB cap (13d9b46) | 01:56 | 03:01 | not shown: build-host scratch still falls (intel1 56 GB, epyc10 45, epyc2 66); applies to new stages only, running kits were not swept |
| r528 tick set-aside, 25-min gate, 45-min ALERT (029426d) | 01:59 | 03:01 | not exercised: 0 set-asides, longest tick since then 7 min. The 02:31-03:00 no-merge gap had no new approvals, so no ALERT was due |
| r529/r530 auto-retire noroot + live-state (ce62040, f63b1a0) | 02:05-02:06 | 03:01 | no: disk-rate log shows AUTO-RETIRE "deleted 0" on 12 of 13 runs (1 delete, epyc10 +48 GB); hub runs rc 1, last intel1 run rc 3 |
| r531 ot-delete / ot-gate-remote on PATH + raw-rm hook (f0034b5) | 02:06 | files only | no: install_path_tools.sh was not run on any host; hook present on localhost only |
| r532 narrowed fail key, LAUNCH-REFUSED once (9c9503b) | 02:10 | 03:01 | partly: refusals 45 -> 4, "recorded once" text seen at 03:04. But sle_sc_v3 / slw_sc_v3 were relaunched at 03:04 on "changed tools" and failed at 03:22 with the same message, the third time |
| r533 measured thread cap (8d2a269) | 02:25 | ot-run yes, ot-heavy no | partly: intel1 committed threads 112 -> 260, waiters 41 -> 24 (2,477 -> 1,107 GB). epyc2 still load 28/128 |
| r536 rt sync guard, 10 snapshots, 100 GB hub floor (5719381) | 03:05 | 03:06 | hub: 20 snapshot dirs, 8.4 GB. Build hosts: 186-187 dirs each, 9.6 GB, not pruned |
| r538 measured gen floor (c6f17fd) | 03:15 | 03:21 | yes: floor 100 -> 61 GB; GEN-DISK-LOW 16 / 13 / 5 lines per hour; only epyc10 and intel1 excluded now |
| r527 hold-release log dedupe (4bd751c) | 01:58 | 03:01 | yes: 500 lines per tick-hour -> 1 summary line per tick (1,500 in hour 02, 9 in hour 03) |

## Kit wave by hour

| | 01:43-01:59 | 02 | 03 (to :43) |
|---|---|---|---|
| LAUNCH | 0 | 0 | 22 |
| ENQUEUE | 1 | 22 | 0 |
| FAIL | 0 | 1 (ENOSPC) | 3 (2 repeat gen, 1 kit_rtl) |
| LAUNCH-REFUSED | 0 | 2 | 2 |
| RELAUNCH-ON-FIX | 0 | 0 | 8 (5 types) |
| SRC-INCOMPLETE (epyc8 s81) | 4 | 12 | 9 |
| GEN-DISK-LOW | 16 | 13 | 5 |
| HOLD-AUTO-RELEASE lines | 500 | 1,500 | 9 |
| ALERT ADOPT-GUARD hbm PLAN_MISSING | 4 | 13 | 9 |
| TOOL-SKEW s81 UNMEASURED / WARN | 4 / 0 | 12 / 0 | 0 / 9 |
| ALERT HUB-SYNC-FAILED | 2 | 8 | 11 |

Tick time: median 153 s, max 264 s (0300: 145 / 462). Rows not launching 79 (WAIT-FORM 25, q_running 22, q_signed
11, KW-FIX-45 8, q_fail 7) plus 74 superseded-event rows. HOLD-AUDIT flat: HELD-BUT-LAUNCHED 0, TERM-UNREACHABLE 3,
HOLD-SUPERSEDED 72. STALE current-event 280 (0300: 252): S81 336 rows (203 FIX-S81-COL-STALE), KV 33, QC 15,
HBM 107, HEAD 1. Unowned 20 (S81 4, QC 1, KV 4, HBM 11; 0300: 19). Merges: 25 in the window, none 02:31-03:00.

## Classes, ranked by fleet time wasted

### A. Hub disk low stops the wave and freezes the tools deploy (about 15% of the window; largest single loss)

Count: 1 event, 105 min without a launch, 118 min without a tools sync, 9 SMOKE-FAIL posts, 1 kit FAIL with
ENOSPC (sle_su_l1__cl5ea486db, 02:54), 1 post appended but not committed. Trend: third hub-floor hold in 3 days
(11-15 10 min, 11-16 46 min, 11-17 105 min).
Root cause: three things share one disk and one condition. (1) The hub floor refuses every launch on every host,
although the hub runs no kit. (2) The refusal is logged once and is not an ALERT, so the 0300 "39 GB" finding had
no actor. (3) The smoke tests that gate rt/current read the live host; with the hub under its floor the Step
tests fail, so the fix for the disk cannot go live. The link between (3) and the disk is from timing (first
SMOKE-FAIL 01:51, last 02:31, first clean sync 03:02, disk freed 02:58); I did not read the test code.
Hub scratch2 is at 173 GB now, falling 21-37 GB/h by the disk-rate log: about 2-3 h to the new 100 GB floor.
Fix:
- (WAVE-FLOW-R) the hub floor holds only what writes to the hub (collect, archive, view packs). Launches to
  build hosts continue. A hold that lasts 2 ticks is an ALERT with the top 5 hub writers.
- (FLEET-OPS-R) rt smoke tests run with a fixed fake host state (free disk, load, held hosts) so they cannot
  read the live hub. 879a437 did this for test_ot_tools_sync only; test_kit_wave Step tests need the same.
- (FLEET-OPS-R) a failed sync leaves a state the autopilot reads: rt/current older than main by 2 merges or
  20 min is one ALERT, not one STATE post per merge.
- (FLEET-OPS-R) lane clones, closed archives and rt snapshots on the hub get a quota each (du per class in
  HOST-REPORT). The 02:50 fill was 3 known classes that no rule owned.

### B. Declared-thread cap still binds; r533 half deployed (about 10-15%, ongoing)

Count: epyc2 threads 144/128 at load 28; intel1 24 waiters / 1,107 GB at load 45/112; epyc7 147/96 at load 42.
Idle 344 of 528 threads at 03:43. Trend: intel1 better (41 -> 24 waiters), fleet use flat (41% -> 43%).
Root cause: the merge changed two files; ot-run runs from rt/current, ot-heavy from /usr/local/bin, which only
a root install step updates. The sync hook reports "hosts ok" without comparing installed files. On epyc7-10
ot-heavy was rewritten at 03:42 with the same old content.
Fix (FLEET-OPS-R): ot-heavy, ot-heavy-reconcile and the PATH tools become symlinks into rt/current (the r423
step, still not applied: regular files on 7 of 7). Then "merged" and "installed" are the same event. Until
then the sync hook compares md5 of each installed file with rt/current and returns non-zero on a difference;
FLOW-HEALTH already has the table for noprog (noprog_stage.py DIFFERS on 7 of 7) and prints NO-INSTALLED for
ot-run.

### C. Build-host scratch (about 10%, ongoing)

Count: epyc10 REFUSED for all jobs (45 GB) while running at load 70; intel1 56 GB, epyc2 66, epyc9 116, epyc7
189, epyc8 235. epyc7 root fs 62 GB < 150 floor (scratch2 only). Three hosts were cleared by hand since 0300.
Trend: same as 0300 (five of six under 100 GB then; three under 70 GB now).
Root cause: unchanged. Admission charges memory, not disk; auto-retire finds nothing to delete because the
space is in running kits and current trees, not in superseded ones. r524 only acts on stages written after
03:01.
Fix (FLEET-OPS-R): the 0300 items stand and none has started: disk charged at admission by measured kit peak
(r538 already measures it for the gen floor: use the same number in ot-run); DISK-RATE under 1 h holds
admissions on that host with an expiry. Add: one pass of the stage-ODB drop over running kits (the watcher
exists in r524; it needs a "sweep existing" mode).

### D. Git mirror cycle is longer than its timer and always fails (gate retries; under 2% compute, slows every merge)

Count: 38 of 38 runs since 01:40 ended "Failed to start"; each takes 3 min 14 s to 3 min 33 s on a 2-min timer
and uses 1 min 55 s CPU; 13 branches (die-s81-51-*-1103, rm63-train*, lec-xfin-1-1103, kv-101-adopt-1113, ...)
are re-forwarded and rejected by GitHub ("pre-receive hook declined") on every run; 1,102 error lines in 2 h.
Trend: not reported before.
Root cause: the mirror retries a rejected push forever, and the rejects sit at the end of every cycle. A new
lane commit is visible to the queue's gate only after the next full cycle, so a gate started inside about
4 min of a push does not find the commit. This fits the QC-TYPES-R 4-min retry loops; I did not find the loop
itself in a log.
Fix (MERGE-QUEUE-1): a push rejected twice with the same sha is recorded and skipped until the sha changes
(one post per branch). Fetch runs first and alone, on its own timer. `ot-gate-remote` waits for the sha in the
mirror (bounded, 10 min) instead of failing, and prints "waiting for mirror".

### E. Relaunch without a fixed cause (about 1% compute; 5 types)

Count: sle_sc_v3 / slw_sc_v3 failed 3 times with one message ("no RTL header for blackbox"): 01:27, then
relaunched 03:04 "changed tools", failed 03:22, now BLOCKED-REPEAT. sle_sc_v1__cl7479a5ec and slw_sc_v2 were
relaunched at 03:00 and again at 03:09, slw_su_l1__clcc9d0155 at 03:00 and 03:23, all with
"changed block+src+overlay+tools+bind_context" (attempt 4 within 9 min of attempt 3; cause not traced).
coll_core kit_rtl FAIL 03:08 and kv3_hg_v1 ("9 filelist path(s) outside") are kit-input errors still filed as
unclassified FLOW; the gen pair is still filed INFRA[tool_mix]. Trend: refusal noise fixed, relaunch cause not.
Root cause: the first sync after a 2-hour freeze changed the stage-tools hash for every stage, so the narrowed
key still opened. REPEAT-STOP needs 3 identical fingerprints, so each such type costs 3 runs.
Fix (WAVE-FLOW-R): same message after a relaunch closes the key at 2, not 3, and posts NEEDS-LANE to the die
types lane. A relaunch records which input changed by name (file list), so "changed tools" can be checked.
The two message texts get a FLOW[kit input] class owned by QC-TYPES-R / KV-R (0300 item, not done).

### F. Delete path: hook without the tool (no compute; data-loss and stall risk)

Count: ot-delete on PATH 0 of 8; raw-rm hook on 1 of 8 (localhost). Trend: worse than 0300 in one way: a lane on
localhost is now refused `rm -rf` and told to use a command that does not exist, which is the same "refusal
looks like not found" condition that produced the 01:11 bypass.
Fix (FLEET-OPS-R): run install_path_tools.sh on all hosts now; the hook checks `command -v ot-delete` and
says so when it is missing. Install is part of the symlink step in B.

### G. READY posts and the coord checkout

Count: 21 READY-type posts since 01:45; 17 state a gate result (GREEN or pass=N/N), 15 name a gate record
path or log. 4 do not: s81-die-r2-bind-defcheck 03:35 (none); s81-fstart-noshared 03:35 (re-posted with a
record at 03:39); one READY-PENDING-GATE at 02:17 (READY with a gate followed at 03:08); one ASK+READY that
hands a commit to another lane. Posts without a tag or lane header: 7 of 122.
lanes/posts/NOPROG-FIX-1115.md carries an uncommitted 02:52 post (append succeeded, commit failed on the full
disk); HUB-SYNC-FAILED has named it on 11 ticks since 02:58. I found no truncated post file; all 54 files
changed since 01:45 are non-empty and end in a full line.
Root cause: post.sh appends before it commits, and nothing retries the commit. READY is free text.
Fix (MQ-PACK-FIX): `post.sh ... READY` refuses unless ~/merge-queue/gates/<sha>.json exists and is GREEN on a
main that is an ancestor of current main; the queue already reads that file. (FLOW-HEALTH) post.sh writes the
post to a temp file, commits, and only then renames; coord-commit at tick start commits any lanes/posts file
that is dirty and ends in a full line.

### H. Noise, stale and unowned rows (tick time, not compute)

Count: ADOPT-GUARD hbm PLAN_MISSING 26 lines on 25 of 25 ticks (HBM is parked); SRC-INCOMPLETE epyc8 s81 on 25
of 25 (same lane-dir path as at 2200); TREE-SWITCH s81 "switched" printed on 25 of 25; kv3_hub_C "no output
for 707 min", reported only; STALE 280 (+28); unowned 20 (+1); superseded-event rows 74; RETIRE-SUPERSEDED
retired 0. kit_wave_state.json and lanes/KIT-WAVE-12.md are still dirty in the hub checkout. Trend: flat; the
skew line for s81 is fixed (UNMEASURED -> WARN at 03:01), after five reviews.
Fix: as at 0300 (alert de-dup by class and key with a counter, `parked` flag for hbm, generated files out of
the checkout, one retire pass for the 203 FIX-S81-COL-STALE rows). Owner WAVE-FLOW-R; FIX-S81-COL-STALE for
the retire pass; COORD for the 20 unowned rows.

## Do now

1. FLEET-OPS-R: install ot-heavy and the PATH tools from rt/current on all 7 hosts (symlink step), and make the
   sync hook fail on an md5 difference (classes B, F).
2. WAVE-FLOW-R: hub floor holds hub writers only, and is an ALERT after 2 ticks; hub is 2-3 h from the 100 GB
   floor at the current rate (class A).
3. FLEET-OPS-R: fixed host state for the rt smoke tests (class A).
4. FLEET-OPS-R: sweep stage ODBs in running kits on epyc10, intel1, epyc2; epyc10 admits nothing now (class C).
5. MERGE-QUEUE-1: skip twice-rejected re-forwards; fetch on its own timer (class D).
