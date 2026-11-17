# FABLE-FLOW-0700: procedural and flow failures, 03:43-06:18 PST

Reviewer: FABLE-FLOW-0700 (Fable). Read-only: no deletes, no kills, no git in owner checkouts. Measured
2026-11-17 05:43-06:18 PST on hub intel2 and the 6 build hosts.
Sources: autopilot/log.txt 03:43-05:43 (26 ticks), lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py (05:44),
`ot-run --status` (05:46), disk-rate log, guard lists and their builders, retire journals on epyc8, a file scan of
scratch2 on epyc8, intel1, epyc2 and of the wave runs on epyc9, lanes/posts since 05:20, CODEX-FLEET-0504 packet.
Previous: FABLE-FLOW-0500. Clock: hub PST; COORD event times ("0500", "0700") run about 60-70 min ahead.
Scope: process and tooling only.

## Headline

1. The disk refills at about 90 GB/h per busy host, and the three retirement tools can only see 14% of it.
   On epyc8, 544 GB of new unshared data appeared in 6 h (91 GB in the last hour). Whole source trees are 38%,
   lane directories (clones and private kits) 33%, wave runs 13%. Auto-retire, retire-superseded and
   disk-autoprune all act on kw45 source trees only, which are 914 GB of 6,633 GB. Nothing automatic retires
   lane directories (2,378 GB), `claude/wt` (1,220 GB, 10 GB new in 24 h) or old wave attempts.
2. The protected list is 97% prose. Of 8,666 roots, 261 come from kit_wave.json and tree-switch markers. The
   other 8,415 are every scratch path printed in 482 handoff files younger than 72 h; 5,186 of them come from
   COORD-REVIEW-QUEUE.md, which holds every post, including the DISK-RATE refusal posts. A refusal therefore
   renews its own protection. 357 entries are whole lane directories (one is `claude/wt`).
3. Two restarted lanes filled epyc7 while I watched. QC-PLAN-R3 ran a raw `git checkout` of main (49 GB) on
   epyc7 scratch2, which went from 41 GB to 1 GB free in 12 min (05:44-05:56); FLEET-OPS-R reports jobs
   failing on write. S81-TYPES-R3 started the same on the epyc7 root disk at 06:06: root went from 46 GB
   free to 10 GB by 06:18 with the checkout at 37 of about 49 GB. I posted three ALERTs (05:56, 06:07, 06:18)
   and stopped nothing.
4. Fleet use: median 49% over 26 ticks (range 35-66%); 0500 was 43%. At 06:00: epyc7 69/96, epyc8 48/96,
   epyc10 55/96, epyc9 10/96, intel1 105/112, epyc2 19/128 = 306/624 (49%). epyc9 sat at load 4-10 on most
   ticks while intel1 held 15 waiters (1,104 GB).
5. Relaunch without a fixed cause is still open after r544: 21 RELAUNCH-ON-FIX in 2 h, every one "changed
   tools" or "changed overlay", 15 fails with 2 messages. sle_ctl is at attempts 20, 23 and 14.

## What fills the disk (main question)

Method: one pass over scratch2 per host, bytes by inode change time, hardlinked files counted once. Change
time is used because tree copies and rsync keep the old modification time: FLEET-OPS-R's 06:03 read by
modification time saw only live kits (13 + 11 + 7 GB in 90 min) and missed trees and clones. Limit: a chmod
also moves the change time, so a tree made read-only late is counted as new. epyc7 and epyc10 scans (about
40 M files each) had not finished at 06:18; epyc7 timed out once at 580 s.

epyc8 scratch2, 6,633 GB unshared plus 563 GB hardlinked, 05:57-06:04 PST:

| Category | Stock GB | New <1 h | New <6 h | GB/h (6 h mean) | Retired by a tool? |
|---|---|---|---|---|---|
| Wave source trees kw45/src_* (37 trees, 48-56 GB each) | 914 | 0 | 207 | 35 | kw45 only, 0 freed |
| Lane directories (clones, private trees, kits) | 2,378 | 45 | 177 | 30 | none |
| Wave runs kw43-wave-1109n (kit copies, stage outputs) | 455 | 5 | 73 | 12 | stage sweep by hand |
| scratch3/claude inside scratch2 and other top-level | 371 | 33 | 35 | 6 | none |
| ot-store objects | 1,011 | 2 | 24 | 4 | none |
| ot-jobs (live wave job dirs) | 34 | 6 | 21 | 3.5 | on job end |
| rt snapshots (203 dirs, oldest 11-15) | 15 | 1 | 7 | 1 | none on build hosts |
| claude/wt, claude/moved | 1,279 | 0 | 0 | 0 | none |
| Old wave-src, closed archives, kit-store, mq-gate | 176 | 0 | 0 | 0 | archives by hand |
| Total | 6,633 | 91 | 544 | 91 | |

- The fall matches: epyc8 went from 276 GB free after the clear to 43 GB at 05:40, about 85-90 GB/h on the
  clear time COORD gave.
- Source trees: 4 whole trees in 6 h: qc s4q9l2_d2 (56 GB), s81 d5c (55), kv hg3b d14 (48, the D14 restore),
  kv kvgeom4_pgL (48, possibly a chmod only). Each D-step is a full unshared copy of 323,767 files; the packet
  says D15 differs from D14 by 52 MB.
- Lane directories: fable-fix-s81-cong/clone_depth 38 GB, fable-fix-s81-svc 51 (19 in the last hour),
  fable-fix-s81-col 26, kv-r/repo3 53 and s81-svcmem wt-serdes 48 in 24 h. epyc8 holds 84 git clones or
  worktrees two levels down, epyc7 69, intel1 52, epyc9 40, epyc10 26, epyc2 22. 16 on epyc8 and 9 on epyc10
  were touched in 24 h.
- ODB files are 31% of the 6-h growth (168 GB) and 62% of the last hour (56 of 91 GB).
- Wave runs on epyc9: 521 GB, 82% ODB. 1,947 older attempts hold 212 GB (41%); 540 latest attempts hold 309 GB.
  290 GB is from the last 24 h.
- intel1 (by modification time): wave runs 294 GB (72 new in 6 h), ot-jobs 137 GB (111 new in 6 h).
- epyc2: mq-gate slot0 wrote 28 GB in 1 h on an 880 GB disk with 55 GB free.
- epyc7 root disk (468 GB, 47 free): /home/ubuntu/scratch-root/claude 324 GB (scratch3 lives on root) and an
  unrelated /home/ubuntu/skyhum-work 42 GB. epyc7 was REFUSED for all jobs at 05:46 on the root floor, not on
  scratch2.

## Why protection keeps dead parts

There are two lists and three retire tools; all three freed 0 in the window (AUTO-RETIRE "deleted 0" on 21 of
the last 22 runs in the disk-rate log).

| List | Used by | Entries | Built from |
|---|---|---|---|
| protected.txt (protected_r362) | ot-delete, retire3, retire-superseded, disk-autoprune | 8,666 | kit_wave.json + markers (261) + every scratch path in handoff text (8,415) |
| protected_struct.txt | auto-retire | 893 | every path string in kit_wave.json: 273 under current keys, 365 under history keys only, 255 other |

1. Text harvest (build_guard_fleetopsr.py). Sources by count: COORD-REVIEW-QUEUE.md 5,186,
   CLEAN-INTEL2-1115.md 1,530 (a cleanup report), PROTECTED-DBS.txt 715. 7,951 roots are named by exactly one
   file. The list grew 8,563 -> 8,623 -> 8,666 over the last three 30-min builds. Truncated strings are in it
   (`kw45/src_`, `kw45/src_k`, `kw45/src_s81_pin_3c913dbdfb23_`): they are the 120-character cut of the
   refusal message, posted by disk_rate.py and read back. They match nothing, but they prove the loop.
2. disk-autoprune prints "named in handoff/queue prose (advisory, does not refuse)" and on the next line the
   delete guard refuses the same tree, because the prose was written into the guard list (epyc8 journal 13:43
   UTC: src_s81_pin_e4b9ae9f1c1f, src_s81_pin_eb1e73448bd0). The message blames kit_wave.json; it is prose.
3. The retirement queue protects its own members. s81 cohort_d3 and d4 (48 GB each, on epyc8, epyc10, intel1)
   are in dies.s81.superseded_trees and under no other key. ot_delete_guard.build_protected drops that key;
   build_struct2.py walks every string and puts it back; 12 and 5 handoff files name them as well.
   retire-superseded logged KEEP for both at 11:48, 12:48 and 13:48 UTC.
4. History keys. kit_wave.json carries src_prev_*, plan_prev_*, kit_rtl_prev_*, note_* back to kw21 (11-06):
   635 paths, 405 under no current key.
5. Source trees per host, by the reason they are kept:

| Host | kw45 and wave-src entries | Current die source | Other current key | History key only | Handoff text only |
|---|---|---|---|---|---|
| epyc7 | 29 | 1 | 0 | 1 | 20 |
| epyc8 | 53 | 5 | 1 | 3 | 27 |
| epyc9 | 54 | 1 | 0 | 0 | 46 |
| epyc10 | 50 | 3 | 2 | 3 | 33 |
| intel1 | 19 | 4 | 1 | 1 | 11 |

   (The rest are sidecar files or unprotected.) epyc9 keeps 46 trees on prose alone, has 1 current tree and
   75 GB free: it cannot take the 4 other current trees, so it is not a gen host for those dies and idles.
6. A whole-tree match is by path component, and any protected path below a tree keeps the whole tree. One
   quoted file path in one handoff holds 48 GB for 72 h, and each new mention restarts the 72 h.

So yes: the list is over-broad. Of the 163 kept trees in the table, 137 (84%) are kept by prose alone: no
current plan key and no history key names them. I did not test each one against live process text; the
guard does that separately and it stays.

## Structural fix for disk (owner FLEET-OPS-R unless named)

1. Protected list from live references only. Sources: current keys of kit_wave.json (src, plan, kit_rtl,
   item_inputs, prov_view_sources, rollback_tree, work_root), tree-switch markers, live attempts in
   kit_wave_state.json, `--dir` and `--stage` of queued and running ot-run clients, and PROTECTED-DBS.txt.
   Remove the text harvest. A lane that needs a hold adds one PROTECTED-DBS line with owner and expiry
   (72 h at most). Drop superseded_trees in build_struct2.py (one line). Keep one generation of *_prev_* and
   move the rest out of kit_wave.json into a history file the guard does not read. Guard messages name the
   source of the match (key or file), and are not cut.
2. One read-only base tree per host and die, D-steps as deltas. A D(n+1) tree is published as its changed
   files plus a manifest naming the base; jobs see the composed tree through a read-only overlay mount
   (lowerdir = delta:base, no upper), which the bwrap job wrapper can bind. Lane private trees use the same
   base with the upper directory in the lane dir, so a chmod or write copies up and cannot reach the
   published inodes. That keeps the 11-16 rule (no `cp -al` of a published tree) and replaces the 48 GB
   `cp -a`. Expected: source trees 35 GB/h -> under 1 GB/h; private trees 48 GB -> the delta. Pilot one D-step
   on one host and compare the manifest hash of the composed view first.
3. Lane clones only through ot-lane-clone (light, shared objects). Both clones I caught were raw
   `git checkout -b ... main` with no sparse list. Add a lane-side hook like block_raw_rm.py that refuses
   `git clone` and a first full checkout under /srv/*/claude and names ot-lane-clone. ot-lane-clone checks
   free space (clone size + floor) and refuses with the hosts that have room. scratch3 on a host where it is
   the root disk is never a clone target.
4. Disk charged at admission by measured peak. ot-run already has `--disk` (default 20 GB) and r538 measures
   kit peak per stage for the gen floor. Charge that peak per (type, stage) and keep a reservation ledger per
   host, so ten launches in one tick do not each see the same free space. Lane scripts get the same charge
   from `--dir` size history.
5. Per-lane quota. du per lane directory per host in the hourly HOST-REPORT (it reports only free GB now).
   A lane over its quota (start at 150 GB per host) gets no new launch on that host and a list of its
   largest children idle for 24 h. This is the retirement path that lane directories lack.
6. Retire by class, not only kw45. (a) Wave runs: keep the latest attempt and any signed attempt per item;
   older attempts drop their ODBs when the next attempt starts (WAVE-FLOW-R; 212 GB on epyc9). (b) rt
   snapshots: the r536 limit of 10 runs on the hub only; build hosts have 203. (c) `claude/wt`: idle
   worktrees older than 24 h with a preserve ref, through the existing guard. (d) ot-reaper cron covers
   localhost, intel1, epyc2 and terminated epyc4 (74 host-key warnings in the log); epyc7-10 are not in it.
7. Replica placement by need. A host gets a die's current tree before it gets a second old one. epyc9 is the
   case: free its prose-only trees first (item 1), then stage the 4 current trees there.

## Are the fixes live

rt/current = 2382f7a6fbac on hub and 6 of 6 build hosts (05:31-05:32); 16 hub syncs in the window, 1 SMOKE-FAIL.

| Fix | Live | Working? |
|---|---|---|
| r524 stage-ODB cap | yes | yes on new attempts: 6 ODBs / 5 GB (serdes__t4 attempt_6) against 15-20 ODBs / 16 GB in attempts started before it. Old attempts keep theirs |
| r530 auto-retire live-state | yes | runs, frees nothing: 21 of 22 "deleted 0" (cause above, not the tool) |
| r533 measured thread cap | yes; ot-heavy is a symlink into rt/current on 7 of 7 | partly: intel1 296/112 and epyc8 288/96 threads committed; intel1 still has 15 waiters at load 65 |
| r536 rt sync guard, 10 snapshots | hub yes (24 dirs) | build hosts no: 203 dirs each, +16 since 0500 |
| r538 measured gen floor | yes (floor 61 GB) | yes; GEN-DISK-LOW 41 lines in 2 h, epyc8 and intel1 excluded at 05:42 |
| r542 mirror skips rejected refs | yes | yes: 14 clean runs and 1 failed start in 30 min (0500: 38 of 38 failed) |
| r543 main-only fetch, 30 s timer | yes (timer active) | yes |
| r544 hub floor holds hub writers; fail key closes at 2 | merged (8566) and in rt/current | hub floor not exercised (0 HUB-DISK lines, hub 134 GB). Fail key: no, see class C |
| r531 ot-delete, ot-gate-remote on PATH | yes, 7 of 7 | yes (0500: 0 of 8) |

## Classes, ranked by fleet time wasted

### A. Build-host disk (about 15% of the window, rising)

Count: epyc7 REFUSED for all jobs at 05:46 and at 1 GB at 05:56; epyc8 and intel1 dropped as gen hosts;
GEN-DISK-LOW 41 lines; 3 manual frees in 3 h (03:00, 03:30, 06:03: 164 and 151 GB freed). Trend: worse than
0500 (one host refused then). Root cause and fix: the two sections above. Owner: FLEET-OPS-R; WAVE-FLOW-R for
old attempts; COORD for the two raw clones (lanes QC-PLAN-R3, S81-TYPES-R3).

### B. Jobs tied to the host that holds their data (about 14%: epyc9 idles 86-92 of 624 threads)

Count: epyc9 at load 4-24 on 7 of 9 sampled ticks (2 bursts over 130); intel1 15 waiters / 1,104 GB at 296
committed threads; about 50 live clients carry a single-host `--hosts` (102 processes, two per client:
epyc8 61, epyc7 18, epyc10 12). Trend: flat since 0500.
Root cause: a lane's clone and kits live on one host, so its jobs qualify only there (ot-run keeps data
locality by `--dir`), and wave kits staged to intel1 wait there. This is the same cause as class A seen
from the load side: 50 GB private trees are too heavy to exist on every host. I did not read each waiter's
host list; the intel1 queue cause is from the status line and the pin counts.
Fix: class A items 2 and 3 make a lane tree small enough to stage on every host; then the owner rule (no
single-host pin) can be enforced in ot-run for kit jobs. Until then WAVE-FLOW-R restages a waiter older than
10 min to a host with room (RESTAGE exists; it fired 10 times in the window). Owner: FLEET-OPS-R, WAVE-FLOW-R.

### C. Relaunch of a cause that was not fixed (about 1% compute; 10 items, 30 of 42 launches)

Count: 42 LAUNCH, 21 RELAUNCH-ON-FIX, 15 FAIL, 3 LAUNCH-REFUSED, class breaker opened 3 times. Two messages:
"param_wrap: base qfd_dv_s8_station_tail1 has no port table" (5 st_a types, failed at 04:14-04:19 and again
at 05:03-05:13) and "hard landing requires SIGNED child and PASS face evidence" (3 sle_ctl types, 04:48,
05:23, 05:28, 05:33; attempts 20, 23, 14). Trend: 0500 had 8 relaunches of 5 types; now 21 of 10.
Root cause: (1) every tools sync (16 in the window) changes the tools hash and reopens the key; r544 scoped
it to the failed stage, but kit_rtl and gen are the stages that failed, so it still opens. (2) "requires
SIGNED child" is a wait condition filed as INFRA[tool_mix]; no tool change can pass it. (3) The 05:19 d2
source change is a real fix candidate for st_a (the packet lists param_wrap changes), so those relaunches
are legitimate; the earlier ones (04:20-05:04, "changed tools" only) were not.
Fix (WAVE-FLOW-R): the key reopens on a tools change only when a file in the failed stage's import closure
changed (TOOL-SKEW already computes that closure per die). "requires SIGNED child" becomes WAIT-CHILD with
the child named, released by the child's sign-off. After 2 identical fails the row posts NEEDS-LANE once.
Restarted lanes: I found no duplicate job. 6 lane jobs started after 05:25 on epyc7-10; the three
hd_serdes routes (sd9d, sd9e, sd9f) are different forms. KV-R3, HEAD-R3 and S81-DIE-R3 show no relaunch
of a failed kit in posts or units. I did not decode the 60 wave job specs.

### D. Stale and unowned rows (no compute)

Count: STALE 284 current-event (0500: 280): S81 338 rows (FIX-S81-COL-STALE 203), HBM 107, KV 34, QC 17,
HEAD 2. Unowned 22 (S81 5, QC 2, KV 4, HBM 11; 0500: 20). Superseded-event rows 69-74; RETIRE-SUPERSEDED
retired 0. Old units still running: 2 type-kvhgi2 routes on intel1 since 11-14 18:04, an hbm-collect kit on
epyc2 since 11-10, 2 yosys mutant runs on epyc9 since 11-15/16. Fix as at 0500 (one retire pass for the 203
rows). Owner: FIX-S81-COL-STALE, COORD for the 22 and for the 5 old units.

### E. Log noise (tick time; median tick 149 s, max 216 s; 0500: 153 / 264)

Count per 26 ticks: ADOPT-GUARD hbm 50 lines (HBM parked), TOOL-SKEW 125 (hbm "241 of 241" each tick),
SRC-INCOMPLETE epyc8 s81 25 (same path since 2200), HUB-SYNC-FAILED 6 (NOPROG-FIX-1115.md still dirty since
02:58), 252 traceback lines for one missing path (s81_head hd_spn_eshim_rx attempt_3, "retry next tick").
Trend: flat; HUB-SYNC lines 11 -> 6. Fix as at 0500 (a `parked` flag for hbm, one line per class and key
with a counter); the eshim row needs a missing-attempt-dir state instead of a retry. Owner: WAVE-FLOW-R.

## Do now

1. FLEET-OPS-R: remove the text harvest from build_guard_fleetopsr.py and the superseded_trees walk from
   build_struct2.py; rebuild; let retire-superseded take s81 d3/d4 and kv hg1A d3/d5 on its next hourly run.
2. COORD: tell every restarted lane that a clone is made with ot-lane-clone on scratch2 of a host with room;
   check epyc7 root (S81-TYPES-R3 checkout, 10 GB free at 06:18).
3. FLEET-OPS-R: free epyc9's prose-only trees through the guard after item 1, then stage the current trees
   of the 4 other dies there.
4. WAVE-FLOW-R: tools-change reopen limited to the failed stage's import closure; "requires SIGNED child"
   as WAIT-CHILD; drop ODBs of non-latest unsigned attempts.
5. FLEET-OPS-R with WAVE-FLOW-R: pilot the base-plus-delta tree on one die and one host (class A item 2).

## Addendum 06:22 PST: epyc7 scan and epyc7 root

epyc7 scratch2, scan ended 06:19 (after the 06:03 manual free; 150 GB free): 6,596 GB unshared, 521 GB new
in 6 h (87 GB/h), 117 GB new in the last hour.

| Category | Stock GB | New <1 h | New <6 h |
|---|---|---|---|
| Lane directories | 4,261 | 57 | 105 |
| Wave source trees kw45/src_* | 500 | 0 | 144 |
| Wave runs kw43-wave-1109n | 397 | 2 | 117 |
| ot-jobs (live wave job dirs) | 96 | 56 | 84 |
| ot-store objects | 839 | 0 | 49 |
| Other (wt/moved 351, old wave-src 50, archives 35, kit-store 32, mq-gate 21, rt 15) | 504 | 1 | 22 |

- Source trees: three KV D-steps of 48 GB each in 6 h (hg3b d12, hg3b_checker d14, hg5 d15).
- Lane directories: the QC-PLAN-R3 clone is 50 GB of the last hour (physical/ 31, .git 10, results/ 9): the
  two directories that ot-lane-clone leaves out are 40 of the 50 GB.
- Idle stock: claude/kw44 524 GB, s87bind 384 GB and s81-leaf-plan 309 GB have 0 GB changed in 24 h
  (1,217 GB). FLEET-OPS-R's 06:03 post says the guard refused whole-directory deletes of s87bind, kw42 and
  wave-src on kit_wave.json references; those are history keys (s87bind appears under prev_kw46_r11p and
  prev_kitops1_r12bA only in my key listing).
- ot-jobs: three live route job dirs for one type, sle_fe_v1__cl1cbb7497 (20, 17 and 15 GB; units started
  11-16 21:09, 22:08 and 23:19 PST, all three processes alive at 05:55). I did not decode which event or
  attempt each belongs to. WAVE-FLOW-R should check them against "one live attempt per item".
- ODB files: 184 GB of the 521 GB (35%).

epyc7 root disk reached 0 MB at 06:21. The S81-TYPES-R3 checkout got to 47 GB in
/srv/opentallas-scratch3/claude/s81-types-r3/wt, failed, and the lane started it again
(`git checkout -q -f -B rck-depth-balance-1117 origin/main`, pid 960862). Nothing was stopped by me.

## Class F (added on COORD request, 06:30 PST): lane code clones are slow or come out empty

Share: no fleet compute; lane wall time. About 10-30 min per restarted lane before its first job, so roughly
2 lane-hours for the 6 lanes of the 05:30 restart, and it is the direct cause of the epyc7 fill in class A.

Measured (clones whose .git was created in the last 8 h, 5 build hosts, 06:25 PST):

| Host | Clone | Kind | Created -> index written | State |
|---|---|---|---|---|
| epyc7 | qc-plan-r3-hlemit-1117 | raw, no filter, full tree | 28 min | whole, 50 GB |
| epyc7 | qc-plan-r3-hlemit-sparse-1117 | blob:none, sparse | 2 min | whole |
| epyc2 | qc-types-r/repo (QC-TYPES-R3) | blob:none, cone physical rtl tools | 12 min (05:55-06:07) | whole, 36 GB |
| epyc9 | kv-r3/repo | blob:none, sparse | 9 min | whole |
| epyc2 | tokr-own/repo | blob:none, sparse | 1 min | whole |
| epyc10 | s81-die-r2-defcheck | blob:none, sparse | at most 79 min | whole |
| epyc7 | wave-flow-r/wfr | blob:none, sparse | at most 122 min | whole |
| epyc7 | s81-types-r3/wt | raw, full, on the root disk | - | HEAD unset, 0 files (disk full) |
| epyc7 | wave-pilot-fix/src | `--depth 50`, no filter | over 7 min, no data yet | HEAD unset, 0 files, running |
| epyc8 | fable-fix-s81-cong/clone_depth | blob:none | - | HEAD unset, 0 files, 38 GB left on disk since 00:49 PST |

"At most" rows: the index time is the last index write, which a later git command also moves. 3 of 10 are
empty. No git process was running on epyc2 at 06:23, so the QC-TYPES-R3 checkout ended at 06:07.

Root causes:
1. Size. main is 328,239 files and 50.2 GB: physical/ 33.3 GB, results/ 15.4 GB, tools/ 0.35 GB, rtl/ 0.92 GB,
   other 0.22 GB. A cone with physical/ is 36 GB even for a pytest run. Everything a code lane edits is 1.5 GB.
2. No local objects. ot-lane-clone expects a shared object store per host
   (/srv/opentallas-scratch2/git/shared/OpenTallas.git); it is missing on 6 of 6 build hosts, and 0 of the 10
   clones have an alternates file. Every blob comes from intel2 at 20-30 MB/s (measured 20 MB/s on the
   QC-PLAN-R3 checkout).
3. Shallow clones are served the slow way. The `--depth 50` clone has had `pack-objects --shallow` on the hub
   for 437 s at 166% CPU and 7.5 GB memory; a shallow request cannot use the pack bitmap. The mirror has
   33 packs with gc.auto 0.
4. Lanes do not use the tool. 3 of 10 are raw `git clone` or `git checkout` with no filter.
5. Failure is silent. A clone that dies leaves HEAD unset and its partial data (38 GB on epyc8). Lanes wait
   with `until ! pgrep -f "git clone ..."`, which matches the waiting shell itself: 9 such loops are still
   alive on epyc2, epyc7, epyc8, epyc10 and intel1, the oldest 23 days.

Fix (owner FLEET-OPS-R; MQ-PACK-FIX for the mirror):
1. One warm bare repository per host with full objects for tools/, rtl/ and the top level, fetched from the
   mirror by the 30 s main timer, listed in the guard list as a structured entry (the 11-13 cleanup deleted
   bare repositories). `ot-lane-clone DIR -b branch` becomes `git worktree add` from it with the cone
   tools/ rtl/: 29,000 files, 1.5 GB, no network, seconds. Each lane keeps its own worktree and branch.
2. For tests on main, use /srv/opentallas-scratch2/claude/rt/current: it is already a tools checkout of main
   on every host, synced at each merge (16 times in this window).
3. physical/ and results/ are not checked out from git on build hosts. A lane reads them from the die's
   current published tree (or the base-plus-delta view of class A item 2). `--with physical` stays for the
   cases that edit plan files and first checks free space.
4. ot-lane-clone refuses `--depth`, checks free space and that the target is not the root disk, prints
   elapsed time and size, verifies HEAD at the end, and removes its own partial directory on failure. The
   lane-side hook of class A item 3 sends raw clones to it.
5. Mirror: repack to one pack with a bitmap after each batch of merges (MQ-PACK-FIX).
6. Lanes wait on the clone's exit status, not on `pgrep -f`. COORD: the 9 stale wait loops and the empty
   38 GB clone on epyc8 have no owner.
