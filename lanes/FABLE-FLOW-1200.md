# FABLE-FLOW-1200: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 12:08-12:55 PST on hub intel2.
Window: autopilot/log.txt 10:00-12:07 PST (FAIL lines read to 12:33), `ot-run --status`, kit_wave.json,
kit_wave_state.json, failure_breakdown.py, NOPROG-TABLE.md (12:15), df / load / ps / journal on 7 hosts, queue posts 10:00-12:36.
Scope: process and tooling only. No physical-design judgement.
Fleet basis: 6 gen hosts, 624 threads. Load at 12:15: about 428 of 624 (69%); 225 ot-run jobs. Shares are estimates unless a count is given.

## Headline

1. A flow fix merged at 11:10 broke kit_rtl on every die whose src tree is older than main. It is still firing
   (class 1). It is the main reason launches fell to 28 per hour.
2. The hub disk filled at 10:35, as FABLE-FLOW-1000 class 3 warned. 28 units died in 4 minutes (class 2).
3. One ROM file missing on epyc8/9/10 (reported at 08:15 and 10:00) still keeps S81 off three hosts. S81 lands on
   epyc7, which is at 99% disk, 92% memory and load 117 on 96 threads, while epyc10 has 5.0 TB and 659 GB free (class 3).
4. The no-progress watchdog cannot fire: 0 NOPROG verdicts of 110 rows (class 4).

## Kit wave, 10:00-12:07

| Window | FAIL | LAUNCH | ENQUEUE | FAIL/LAUNCH |
|---|---|---|---|---|
| 2 h | 84 | 101 | 82 | 0.83 |
| 10h | 54 | 67 | 48 | 0.81 |
| 11h | 24 | 28 | 25 | 0.86 |

At 10:00 the 2 h figures were 194 / 265 (0.73). Fails fell by 57%, launches by 62%. The ratio did not improve.
Launches by die: QC 74, S81 15, KV 7, HEAD 5. S81 has 373 of 398 items on hold (class 7).

| Count | Stage | Class | P | State at 12:35 |
|---|---|---|---|---|
| 28 | unit | hub disk full: `OSError [Errno 28]` in run-item on intel2 | P | one burst 10:35-10:38; hub root now 265 GB free |
| 18 (+14 to 12:33) | kit_rtl | `bind.py: unrecognized arguments: --src-tree` (12 of the 18 logged as "KW_ROAM") | P | firing every tick |
| 14 | place | false place fail "RC=0 but no 3_place.odb" | P | falling: last one 11:33 |
| 10 | gen_lint | S81 `defparam LOCAL` | P | stopped 10:53 (held 10:51; 4 released 12:29 after the merge) |
| 3 | gen | KIT_NOT_SELF_CONTAINED (QC sle_ctl, signoff.json in a lane dir) | P | blocked at 3x, then relaunched 11:23 |
| 2 | place | S81 svc_hi "INFRA @place" whose evidence line is a yosys pass name | P | mislabel, cause not read |
| 2 | gen | QC hard-landing proof / evidence file missing in qc-s29-tree2 | mixed | open |
| 7 | place | KV clock-landing band | design | out of scope |

75 of 84 fails are procedural.

## Summary, ranked by waste

| # | Class | Count | Trend vs 10:00 | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Wave passes `--src-tree` to a src tree's old bind.py | 32 fails; 40 kit_rtl RC=2 vs 67 RC=0 since 11:00 | new at 11:33, rising | under 1% CPU; blocks every new QC/S81 item on those trees | SRC-TREE-1115 |
| 2 | Hub disk full | 28 units | predicted, happened once | about 1-2% (28 attempts lost, most S81 col_h9) | CLEAN-ALL-1115, FLOW-HEALTH-1 |
| 3 | S81 src incomplete on 3 hosts; epyc7 overloaded | 36 SRC-INCOMPLETE lines; same file since 08:15 | flat, third review | about 5-8% (S81 slowed on epyc7; 3 hosts closed to S81) | SRC-TREE-1115, KIT-OPS-5 |
| 4 | No-progress watchdog cannot fire | 81 of 110 rows EXCLUDED, 17 YOUNG, 0 NOPROG | new finding | about 8% (49 openroad over 6 h, about 50 cores) | WAVE-PREPNR-1115 |
| 5 | False place fail | 14 | 58 -> 14, falling | under 1% | WAVE-COPYBACK-1115 (closing) |
| 6 | Retries on an unfixed cause; the 3x block misses | slice_station__t8 at attempt 27; 6 items x 3-4 fails in 1 h | open | under 1% CPU; one fail per item per tick | FLOW-HEALTH-1 |
| 7 | Holds without a release condition | S81 373, HBM 107, QC 46, KV 42, HEAD 9 | S81 316 -> 373 | none direct; S81 launches 15 in 2 h | WAVE-HOLDS-1115 |
| 8 | Adoption switches before the plan is on every host | 3 ADOPT-GUARD alerts at 10:52 (QC S4Q3B) | open (0815 class 4) | not measured | KIT-OPS-5, SRC-TREE-1115 |
| 9 | scratch2 at the floor on epyc7/epyc8 | epyc7 106 GB (99%), epyc8 156 GB (98%) | epyc7 worse (376 -> 106) | 0 now; epyc7 holds 73 jobs | CLEAN-ALL-1115 |
| 10 | Lane clones with the owner checkout as origin | 49 of 164 clones (2 levels deep), 0 on GitHub | helper merged 11:46; sweep not done | none | MERGE-QUEUE-1 |
| 11 | Bookkeeping | STALE 143 current (+165 superseded); 57% repeat log lines; tick 285 s | STALE count fixed; rest flat | none | FLOW-HEALTH-1 |

## 1. Wave passes `--src-tree` to an old bind.py (new, still firing)

Measured:
- kit-rtl-src-tree-1115-3 merged 11:10 (main dd72c6d80e3). kit_wave.py line 5726 now adds `--src-tree <src>` to the
  kit-rtl command. The command is `cd <die src tree> && python3 tools/die_plan/bind.py kit-rtl ...`: it runs the src
  tree's own bind.py.
- `grep -c -- --src-tree` on that file returns 0 in wt/qc-s29-tree2 (intel1), s81-b3-clk B6gsh/src_rel2 and
  B6gsl/src (epyc7).
- First fail 11:33. 18 fails to 12:07 and 14 more to 12:33 (QC 28, S81 3, KV 1). Unit logs since 11:00:
  kit_rtl RC=2 40 times, RC=0 67 times.
- 12 of the 18 are logged "unclassified @kit_rtl: KW_ROAM kit_rtl: ran on X, outputs copied back to Y". The same
  items alternate between that text and the argparse text on successive attempts, and RC=2 is the argparse exit code.
  I read this as one class. I did not open a remote kit_rtl log of a KW_ROAM-labelled attempt to confirm.
- No lane has posted it. The wave posts it to DIE-QC-101 and DIE-S81-90 as 12-16 "events" per tick.

Root cause in the process: the fix for one skew (stale baked RTL) added a new one. The wave (main) and the tool it
calls (the src tree) are versioned apart, and the merge gate tests the wave against main's bind.py only.

Structural fix:
- The wave calls main's tool on the tree's data: `python3 <rt/current>/tools/die_plan/bind.py kit-rtl --src-tree <tree>`.
  A src tree supplies RTL and plan data, never the tool. Then no wave change can outrun a tree.
- Until then: one capability probe per (tree, tick) (`bind.py kit-rtl --help | grep src-tree`); without it the wave
  omits the flag and logs one SRC-TOOL-OLD line per tree.
- Gate rule: a wave change that adds an argument to a src-tree tool carries a test against the oldest live tree.
- src-tree-manifest merged at 12:34. Its rollout (r129: QC -> S81 -> HEAD -> KV) must rebuild each tree from main,
  which also clears this class. QC first: it has 28 of the 32 fails.

## 2. Hub disk full (28 units in 4 minutes)

Measured: 10:35:29-10:38:39, 28 FAIL "INFRA @unit: OSError [Errno 28]" (S81 23, QC 2, KV 1, HEAD 1, +1). The
traceback is `write_text` in run-item on intel2. At 10:00 hub root had 29 GB and scratch2 28 GB. Now root 265 GB
(41%), scratch2 204 GB (94%). epyc2-scratch3 merged 10:53. No hub-disk ALERT line exists in the log.

Root cause: unchanged from 10:00. The hub has no floor of its own; run-item writes state until the disk is full.

Structural fix (repeat of 10:00, not done): hub free space is a tick precondition. Below 20 GB the tick posts one
ALERT and launches nothing. Run-item treats ENOSPC on the hub as "wait and retry the write", not as an item FAIL:
the remote job is still good. The 28 rows should be uncharged (they are INFRA) and their remote work re-adopted.

## 3. S81 src incomplete on three hosts, so S81 piles on epyc7

Measured:
- SRC-INCOMPLETE fires every tick for epyc8, epyc9, epyc10: `B6gsl/src/physical/asap7_memory_macros_v2/
  ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v missing`. Those dirs hold only the .v; epyc7 has .json, .lef, .v.
  intel1 and epyc2 do not have the directory at all. Same file as at 08:15 and 10:00.
- epyc7: scratch2 106 GB free (99%), memory 922 GB used / 85 GB available, load 117 on 96 threads, 63 openroad,
  73 ot-run jobs. About 45 of them are S81 col_h9 pv-sibling GRT runs.
- epyc10: 5.0 TB free, 659 GB memory available, load 65. epyc9: 2.0 TB, 575 GB. epyc8: 617 GB memory.

Root cause: the wave correctly refuses a host whose copy is not whole, and nothing copies the missing file. The
refusal is logged 18 times an hour and owned by no one.

Structural fix: SRC-INCOMPLETE is an action, not a log line. The tick that finds a missing file on host B and the
file present on host A copies it (rsync of the listed paths only) and re-checks next tick. The new src manifest
(merged 12:34) gives the file list; the replication step must use it. Second miss on the same file posts one ASK
to the die owner. Today: one rsync of that ROM directory from epyc7 to epyc8/9/10 opens three hosts to S81.

## 4. No-progress watchdog cannot fire

Measured in NOPROG-TABLE.md 12:15: 110 rows = EXCLUDED 81, YOUNG 17, PROGRESS 7, KEEP 3, NO-DATA 2. NOPROG 0.
- All 81 EXCLUDED rows say "plan priority job (bind/LATCHECK/G0/die-proto)". They are ordinary kit-wave P&R
  (col_h9 GRT, kv3_pv, hd_ctl, serdes). No ot-run process on epyc7 carries `--priority plan` (0 of 259).
  `is_plan()` also matches PLAN_RE on the command text, and PLAN_RE includes `strict[-_ ]?bind`, `g0`, `latcheck`.
  Kit paths and commands contain such tokens (for example bind dirs), so nearly every row matches. I did not
  find which token matches; the count shows the test is wrong.
- YOUNG: intel1 has five GRT jobs 13.6-17.9 h old with a flat repair_TNS (for example 500872 best = last) judged
  "series started inside the last 6 h". The series restarts, so age never accrues.
- openroad over 6 h now: epyc2 13, intel1 8, epyc7 4, epyc8 2, epyc9 10, epyc10 7 = 44 (49 at 10:00); 30 over 12 h.

Root cause: the exclusion is a text match on a command line that carries path names, and the evidence clock resets
with the log series instead of using the process start.

Structural fix: exclude on the declared priority only (OT_HEAVY_PRIO=plan in the unit environment). Evidence age =
time since the best value of the metric, bounded by process age, across series restarts. The table prints the
matched token for each EXCLUDED row. A table with 0 NOPROG and over 20 jobs older than 12 h posts one ALERT.

## 5. False place fail (closing)

14 in the window (58 at 10:00), last at 11:33. wave-copyback-2 merged 10:35 and placed-scan 10:45. One
COPYBACK-REJUDGE line (10:46, 1 row). Live run-item processes on the hub: 18, on rt 99795561e0b7 (12),
fcf88eddbfa3 (2), c792e43916cb (2), dd656c7acb39 (2); all four include the fix. Six kw38/rt legacy processes
remain (QC glue, native59). Expect 0 next window. The 10:00 fix "judge from rt/current" is still not done:
118 rt/<sha> trees sit on hub scratch2.

## 6. Retries on an unfixed cause; the 3x block misses

Measured: s81/slice_station__t8 is at attempt 27. QC cbn_q00__cldbcda913 ran attempts 4, 5, 6 between 11:43 and
12:33; cbn_q01 (2 forms), sle_hc2 and cbx_q10 the same. BLOCKED-FLOW "same failure 3x" fired 8 times in the
window, but not for class 1: the fail text alternates between "KW_ROAM ..." and "bind.py: error ...", so the
signature never repeats 3 times. sle_ctl__cl503337ff was BLOCKED at 10:15 and failed again at 10:45 and 11:23.
flow-health-1115b (signature breaker) is not merged: 0 CLASS-HOLD lines, no lanes/FLOW-HEALTH.tsv.

Root cause: the block key is the free text of the last log line, per item.

Structural fix: the key is (die, stage, exit code, normalised first error line), counted across items. Host names
and paths are stripped. "KW_ROAM" is a progress line and is never the evidence line. A stage with RC != 0 and no
error line is class "kit_rtl RC=2", not "unclassified". 3 items in 30 min on one key holds the key for the die.
BLOCKED means no relaunch until the owner clears it; the 11:23 relaunch shows it does not.

## 7. Holds without a release condition

Measured in kit_wave.json: S81 373 hold_items of 398 items (316 at 10:00), HBM 107, QC 46, KV 42, HEAD 9.
- S81: PENDING-PLAN 83, COL-INHERIT 111, FABLE stop list of 11-14 79, WAVE-HOLDS 10:51 46, other 54.
  WAVE-HOLDS kept 10 LOCAL items "in the B6gE 250 list" after the fix merged (12:29 post). B6gE is not adopted;
  the list holds types for a plan that has no adoption time.
- HBM: 25 + 5 "SUPERSEDED KW-FIX-45 11-11" rows and 6 "WAIT DIE-HBM-97" rows of 11-09. HBM is parked, so no cost.
- HEAD: all 9 holds are "SIGNED OFF" notes. They are records, not holds.
- Leak: QC slw_su_c launched against its hold (fixed 10:59 by a wildcard key). KV pv types failed 5 times after
  the 10:52 hold because in-flight attempts are not stopped by a hold. HBM: 22 plan cores are dropped every tick
  (PLAN-CORE-NOT-IN-ONLY, 12 lines).
- WAVE-HOLDS-1115 now verifies each hold on origin/coord/state and posts the lift condition in text. That is the
  right habit; it is still text.

Structural fix (10:00 class 6, not done): each hold_items entry is {owner, reason, release: branch-merged |
event-adopted <name> | date}. The tick releases it when the condition is true and lists entries with no condition
or a condition older than 24 h. Signed items leave hold_items. A hold says whether in-flight attempts stop.

## 8. Adoption before the plan is on every host

10:52 QC S4Q3B: ADOPT-GUARD PLAN_MISSING on epyc8 and intel1 (plan json unreadable) and plan_sha256 not set.
WAVE-HOLDS staged plan, runtime and bind to epyc8 after the switch (10:59 post). 17 QC items launched 10:5x.
QC launches after 10:5x all carry event-key S4Q3B and plan sha 0b264144a3d5. The S4Q2 kit dirs still in use
are the 53 REKEY rows ("plan block unchanged, keeps running"): unchanged-input types, not superseded-plan
launches. SKIP-OLDPLAN stopped 2. The wave state still lists 25 ENQUEUED rows on S4Q2 and 11 on S3R; I did not
check whether any of them can launch.

Structural fix: the adoption command stages and verifies first, switches second (0815 class 4). With the src
manifest merged, ADOPT-GUARD can refuse the switch instead of alerting after it.

## 9. scratch2 on epyc7 and epyc8

epyc7 106 GB free (376 at 10:00), epyc8 156 GB (268), intel1 361 GB, intel2 204 GB. ot-run still admits both.
CLEAN-ALL-1115 (11:5x): on epyc8 claude/wt is 2.5 TB and 2.2 TB of it is protected by keep lists (bind and
filelist references, hub kit_wave list, clean4-kw-src list). 20% free is not reachable under the standing rules.
No admission or disk refusal appears in the user journals of the 7 hosts in the last 2 h.

Root cause: a keep protects a whole tree when a live job references one file in it, and src trees are full
copies. Class 3 adds to it by sending S81 to the fullest host.

Structural fix: keeps are per file list (the src manifest), not per tree; the rest of a tree is deletable.
Src trees are stored once per host by content (ot_store hardlinks, read-only) so N lanes cost one copy.
The wave weighs free scratch when it picks a gen host. Fixing class 3 moves S81 load off epyc7 today.

## 10. Lane clones

Clones found two levels under scratch2/claude: epyc7 49, intel1 49, epyc8 34, epyc9 19, epyc2 11, epyc10 2 = 164.
Origin is the hub checkout on 49 (epyc7 21, epyc8 12, epyc9 8, intel1 5, epyc10 2, epyc2 1). Origin is GitHub on 0.
The COORD figure of 311 comes from a deeper scan; I did not repeat it. ot-lane-clone merged 11:46 and
`ot-merge-queue gate` 11:41, installed on 7 hosts 12:35. The origin sweep and the push refusal on the owner
checkout are not done. Approvals: r130 and r132 did not parse (11:20, 11:25 ticks); mq-approve-list merged 11:47.

## 11. Bookkeeping

- STALE: 143 current-event, 165 on superseded blocks now counted apart (fixed). S81 unowned 142, mostly DEDUP and
  CANCELLED rows of 11-14. Live check NOT SEEN: intel2, epyc4.
- Log repeats in the window: DEDUP 732 + RETRY-IGNORED 458 = 57% of 2,088 lines. ARCHIVE FAILED 12, one sha
  (3054c87a89d6, probe traceback) every tick.
- Tick time 285 s: kit_wave_step+admit 165 s, loop_gaps 64 s, reviews_retry 36 s. One tick per 10 min.
- HUB-SYNC-FAILED 5 alerts (lane edits left uncommitted in the hub checkout: bin/post.sh, tools/stale_list.py,
  lanes/STALE.tsv). DRIFT: /usr/local/bin/ot-oom-age differs from main on all hosts (56 lines).
- Unowned in failure_breakdown: QC 3 cores and HBM 8 cores with no kit-wave row; S81 dsdv_gunit_l1f_bf no row.

## Did the 10:00 fixes land, and did they work

| 10:00 item | Landed | Worked |
|---|---|---|
| wave-copyback 1+2, placed-scan | 09:38, 10:35, 10:45 | yes: 58 -> 14, last 11:33 |
| kit-rtl-src-tree-1115-3 | 11:10 | LOCAL class stopped; it created class 1 |
| epyc2-scratch3 | 10:53 | epyc2 scratch 265 GB, admits |
| mq-ready-gate-skip, mq-gate-cmd, mq-lane-clone, mq-approve-list, src-refresh-mergeguard | 09:56-11:47 | merge fails 2 in the window (9 before); 16 merged |
| src-tree-manifest | 12:34 (1 MERGE-FAIL at 11:16) | not rolled out to any die yet |
| s81-typemerge-impl | 10:59 | out of scope |
| flow-health-1115b (breaker, skew check, FLOW-HEALTH.tsv) | NO | class 6 open; no skew check on the hub |
| Hub disk precondition | NO | hub filled at 10:35 (class 2) |
| r122 LOCAL hold | applied 10:51, 85 min after the ruling | 10 more fails first |
| Reaper reads CPU / watchdog | NO | class 4 |
| S81 ROM file on epyc8/9/10 | NO | class 3 |
| Typed holds with release condition | NO | class 7 |
| Origin sweep, push refusal on the owner checkout | NO | class 10 |

## Order of work

1. SRC-TREE-1115: class 1 now. Wave calls main's bind.py, or probe and omit the flag. Then the manifest rollout, QC first.
2. KIT-OPS-5: rsync the S81 ROM directory from epyc7 to epyc8/9/10 (class 3). Minutes of work, three hosts gained.
3. WAVE-PREPNR-1115: watchdog exclusion on declared priority only; evidence age across series (class 4).
4. FLOW-HEALTH-1: merge flow-health-1115b with the class key of section 6; hub disk precondition (class 2).
5. WAVE-HOLDS-1115: typed release conditions; drop the 9 HEAD and the superseded HBM entries (class 7).
6. MERGE-QUEUE-1: origin sweep of the 49+ clones (class 10).

## Not checked

- The KW_ROAM = `--src-tree` link rests on alternation and RC=2, not on a remote log.
- Which PLAN_RE token matches the 81 EXCLUDED rows.
- Whether the 44 long openroad jobs make progress.
- Whether the 17 QC launches at 10:5x failed because the plan was missing on epyc8/intel1.
- Clone origins below two directory levels; localhost and epyc4 were not probed.
- CLEAN-ALL's 2.2 TB protected figure on epyc8 is quoted from its post, not re-measured.
- The src skew check: I found no such tool on the hub to run.
