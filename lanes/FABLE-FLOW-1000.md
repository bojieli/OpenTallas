# FABLE-FLOW-1000: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 09:49-10:12 PST on hub intel2.
Window: autopilot/log.txt 07:50-10:06 PST, `ot-run --status`, kit_wave.json, kit_wave_state.json, failure_breakdown.py,
df / loadavg / ps on the 6 gen hosts, queue posts and rulings r121-r124.
Scope: process and tooling only. No physical-design judgement.
Fleet basis: 6 gen hosts, 624 threads. Load at 10:00: 458 of 624 (73%). Waste shares are estimates unless a count is given.

## Kit wave, last 2 h

| Window | FAIL | LAUNCH | FAIL/LAUNCH |
|---|---|---|---|
| 2 h (07:50-09:50) | 194 | 265 | 0.73 |
| 1 h | 95 | 102 | 0.93 |
| 30 min | 27 | 18 | 1.50 |
| 09:35-10:06 | 27 | 33 | 0.82 |

Per hour today: 05h 39/29, 06h 246/303, 07h 103/113, 08h 146/199, 09h 48/66 (to 09:50).
The 0815 review measured 0.84. The ratio has not improved; launches fell (303/h -> about 100/h).

2 h by class and stage (procedural classes marked P):

| Count | Stage | Class | P | State at 10:06 |
|---|---|---|---|---|
| 58 | gen | S81 STALE-CORE-VIEW cfg7 55 / vsw 3 | P | stopped 09:00, post-fix gens pass |
| 58 | place | false place fail: 27 "PLAN GRTM edge_outline" + 20 "unclassified KW_PLACE_RC=0" + 11 "INFRA no 3_place.odb" | P | still firing: 11 at 09:57 |
| 22 | kit_rtl | HEAD "bootstrap GEN failed" (phy_pg_floor_um schema skew) | P | stopped 08:40 (hand patch, see class 5) |
| 22 | gen_lint | S81 `defparam LOCAL` (stale baked asbuilt.base src) | P | still firing: 13 after the r122 hold |
| 7 | gen/place | QC units killed by a lane script (signal 15 from /tmp/s4q2sw.py) | P | one event at 08:0x |
| 7 | gen/kit_rtl | KIT_NOT_SELF_CONTAINED | P | flat, 1-3 per hour all day |
| 7 | disk | no host qualifies / disk floor | P | one burst at 08:00 |
| 4 | kit_topology | captured source cohort lacks topology prep (file missing) | P | open |
| about 30 | gen_lint, place, LEC | module not in design 2, clock-landing band 7, Tcl cland_col_cursor 5, sim/yosys killed 10, other | design or mixed | out of scope |

About 185 of the 194 fails are procedural. No class circuit breaker fired (0 CLASS-HOLD lines): it is in
claude/flow-health-1, which is still not merged.

## Summary, ranked by waste

| # | Class | Count | Trend | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | False place fail, fix not reaching in-flight items | 58 in 2 h; 67+ today | not falling yet | about 3-6% CPU; 2-4.5 h calendar per hit | WAVE-COPYBACK-1115 |
| 2 | Long-running P&R with no owner | 49 openroad over 6 h (was 76) | falling | about 10% (65 cores) | WAVE-PREPNR-1115 (reaper), KIT-OPS-5 |
| 3 | Hub and scratch disks at the floor | intel2 scratch2 100% (28 GB), root 94%; epyc2 64-118 GB | intel2 worse, epyc2 marginal | 0 now; epyc2 = 20% of threads at risk; hub full stops everything | CLEAN-INTEL2-1115, CLEAN-EPYC2-1115 |
| 4 | In-place edit of shared source trees (hardlink) | 58 fails, 233 paths, 4 hosts | stopped 09:00 | under 1% CPU; S81 gens dead 08:38-09:00 | KIT-OPS-5 |
| 5 | Die src and tools versioned apart; live hand patches | 22 + 22 + 4 fails; 23 + 3 files patched live; kw38/rt drift 48 files | rotating | under 1% CPU; 1-2 h per die | KIT-OPS-5, FLOW-HEALTH-1 |
| 6 | Holds ruled but not applied; retries on an unfixed cause | 13 LOCAL fails after r122; 9 items each failed 2-3 times | open | under 1% CPU | KIT-OPS-5 |
| 7 | Flow-fix branches bounce in the merge queue | 40 MERGE-FAIL, 68 MERGED, 3 BOUNCE today; flow-health-1 failed 2 times | rising (14 at 07:45) | none; every class above waits on it | MERGE-QUEUE-1, FLOW-HEALTH-1 |
| 8 | Lane clones use the owner checkout as origin | 24 clones on 3 hosts; 68 claude/* refs pushed there today | open, barred by r124 | none; 2 bad gate stamps today | MERGE-QUEUE-1 |
| 9 | Lane kills units by script | 7 QC units | one event | under 0.5% | KIT-OPS-5 |
| 10 | Bookkeeping: STALE, log repeats, time stamps | STALE 295 (139 S81 unowned); 1,791 repeat lines of 3,023; 48 wrong stamps | flat | none; hides real rows | FLOW-HEALTH-1 |

## 1. False place fail (about 3-6% CPU, the largest calendar loss)

Measured:
- 58 fails in 2 h under three labels for one cause: place exits 0, the probe looks on the wrong host, the row fails.
- WAVE-COPYBACK merged at 09:38 (main 1faf0c24936); rt/current is b89ba8df4f0a on the hub and all 6 gen hosts.
- It still fired 11 times at 09:57. "3_place.odb found on" appears 0 times in the wave log.
- Cause of the lag: each run-item process is pinned to the rt/<sha> tree of its launch. Of 202 live run-item
  processes, 20 run on 1faf0c249364 or later. 178 run on 9 older trees (82 on f87021159086) and 4 on legacy kw38/rt.
  Every one of those that reaches place can still false-fail.
- The tick does run new code: auto-rejudge at 09:50 reclassified 29 rows.
- Sampled attempts ran 149-276 min at 2-8 threads before the false fail. That is the basis of the share.

Root cause in the process: a wave fix applies only to items launched after it. Nothing re-judges or restarts in-flight
items, and the same event is logged under three class names, so its size was hidden until 09:2x.

Structural fix:
- The judge step (after_place, copy-back) runs from rt/current, not from the launch-pinned tree. Only the kit recipe
  stays pinned. Then a merged judge fix covers every in-flight item at once.
- Until then: the tick re-judges every place FAIL of an old-tree process before charging it (the 09:50 rejudge shows
  the path exists; make it run each tick, not once).
- One class name for "RC=0, no odb". WAVE-COPYBACK posts the after-fix rate split by launch tree.

## 2. Long-running P&R with no owner (about 10%)

Measured: openroad over 6 h: epyc2 14, intel1 8, epyc7 6, epyc8 2, epyc9 10, epyc10 9 = 49, using 65 cores.
26 are over 12 h. At 07:46 it was 76 processes and 83 cores.
RUNNING rows on a non-current event: 4 (QC 2, S81 2). At 07:46 it was 21.
REAP-DEAD lines: 112 in 2.2 h (was 398 in 2.7 h).
wave-longrun-1 merged 09:00 and oldplan-block merged 08:50. Both worked in part.

Root cause: unchanged from 0815. The reaper still only reports. I did not check which of the 49 make progress.

Structural fix: the reaper reads unit CPU time; zero CPU for 30 min is dead and is reaped. One live attempt per
item. The 4 old-event rows are re-keyed or cancelled at adoption, in the same tick.

## 3. Disks at the floor

Measured at 10:00:
- intel2 (hub): scratch2 100% used, 28 GB free of 3.5 TB. Root and scratch3 are one disk, 94%, 29 GB free.
  ot-run refuses intel2 (floor 150). The wave state, the queue, rt/ and the merge-queue clone all live there.
- epyc2: scratch2 118 GB by df, 64 GB by ot-run status. It admits now. It was refused at 48 GB at 09:4x.
  Its root has 1.8 TB free, 46% used.
- epyc8 scratch2 97% (268 GB free), epyc7 95% (376 GB), intel1 90% (365 GB).
- claude/epyc2-scratch3-1115 MERGE-FAILed at 08:59 (its test timed out at 600 s). Not merged.
  alert-nonsticky: no merge, no post today.
- No post today from CLEAN-INTEL2-1115 or CLEAN-EPYC2-1115 in the queue.

Root cause: one fixed scratch path per host, and cleanup is the only lever. The hub has no alarm of its own: a full
hub disk stops the wave state write, and that looks like a quiet fleet.

Structural fix:
- ot-run picks the scratch disk with the most free space per host (the epyc2-scratch3 branch; fix its test timeout).
- Hub disk is a tick precondition: below 20 GB the tick posts one ALERT and stops launching, instead of failing writes.
- rt/<sha> trees and kit_wave/<item>/a<N> dirs with no live process are pruned by the tick that retires them.

## 4. In-place edit of shared source trees (58 fails)

Measured: 08:38-09:00, 55 cfg7 and 3 vsw STALE-CORE-VIEW fails. One lib inode was shared by 192 paths on epyc7
and 41 on epyc8/9/10, across 19 lanes. One in-place write changed all of them. No signed dir was hit (DIE-S81-92).
The gate that caught it is correct. Each item failed once: the gate is deterministic, so cost was low.

Root cause: source trees are cloned with hardlinks (cp -al), and any lane may write through a link.

Structural fix: published src trees and views are read-only (chmod a-w at publish, by the replication step).
A change is a new directory plus a pointer switch. The tools' install step uses copy+mv only. With that, a write
through a link fails at the writer, not 20 lanes later.

## 5. Die src and tools versioned apart; live hand patches

Measured:
- HEAD phy_pg_floor_um: 22 kit_rtl fails 08:20-08:40. The key existed in a lane overlay tree, not in main.
  KIT-OPS-5 patched 3 files by hand into src_head_rp21z_pgcaplec_c327.
- S81 `defparam LOCAL`: 22 fails. kit-rtl took one file from the stale baked asbuilt.base. The fix
  kit-rtl-src-tree-1115-2 MERGE-FAILed at 09:33 (2 new red tests). Not merged.
- WAVE-COPYBACK class B: 23 die-src copies patched live on 6 hosts.
- Hub legacy tree kw38/rt: 48 files differ from its HEAD, 4 live processes (MERGE-QUEUE DRIFT 08:52).
- SRC-INCOMPLETE: 46 lines. S81 B6gsl is missing a ROM file on epyc8/9/10 (same as 0815, still open).
  HEAD pgcaplec_c327 is missing bind.py on epyc2/8/9.
- The src skew check does not exist on the hub: no "skew" tool under tools/fleet or tools/autopilot in rt/current,
  no lanes/FLOW-HEALTH.tsv, 0 SKEW lines in the log. It is in the unmerged flow-health-1 branch.

Root cause: a die's src tree is a hand-made copy that drifts from main, and each fix is hand-applied to N copies.
Adoption verifies the plan json, not the tree the kits read.

Structural fix:
- A die src tree is built by one command from (main sha + named overlay list) and carries a manifest with both.
  kit_wave refuses a src tree with no manifest or with a file that differs from it.
- Adoption switches the event only after the manifest verifies on every gen host (0815 class 4, not done).
- A live patch is a new overlay entry, not an edit. kw38/rt is retired once its 4 processes end.

## 6. Holds ruled but not applied; retries on an unfixed cause

Measured: r122 (09:26) ordered a hold on the 9 S81 LOCAL items. At 10:05 none of the 9 is in s81 hold_items.
13 of the 22 fails came after the ruling. All 9 items failed 2 or 3 times. The item block at 3 is the only stop.
hold_items now: S81 316, HBM 107, QC 56, KV 36, HEAD 9. Nothing lists which of these have a live release condition.

Root cause: a ruling is text. A hold becomes real only when a lane edits kit_wave.json by hand, and the same
gen_lint signature may relaunch because gen_lint fails are charged per item, not per signature.

Structural fix:
- A hold is posted as a machine line ("HOLD die class-signature until <branch> merged"). The tick applies it and
  releases it when the named branch is on main. No hand edit, no forgotten release.
- Same deterministic signature on 3 items in 30 min holds the signature (the flow-health-1 breaker).
- Each hold_items entry carries owner, reason and release condition. Entries without one are listed hourly.

## 7. Flow-fix branches bounce in the merge queue

Measured today: 68 MERGED, 40 MERGE-FAIL, 3 BOUNCE. Since 08:00: 9 MERGE-FAIL, 2 BOUNCE.
- flow-health-1 failed at 08:31 (7 tests) and 09:00 (1 test). It has been READY since before 07:45.
- kit-rtl-src-tree-1115-2 (r122) failed at 09:33. epyc2-scratch3 failed at 08:59 on a 600 s test timeout.
- The gate-stamp check had a live bug (.strip() on a CompletedProcess) that stopped the check for every valid
  stamp. It also bounced an already-merged branch at 09:08. Both fixed by mq-ready-gate-skip, merged 09:56.
- 11 test_kit_wave* tests fail on main (26 baseline failures in the 09:38 gate). r122 gave them to FLOW-HEALTH-1.

Root cause: the gate a lane runs (its touched test files) is narrower than the gate the queue runs (140 files),
and a red baseline makes "same failures as main" a manual comparison.

Structural fix:
- One command, `ot-merge-queue gate <branch>`, runs the queue's own gate on origin/main and writes the stamp.
  READY without that stamp is rejected. Lanes stop choosing their own test list.
- Main baseline goes to 0 red: fix or quarantine the 26 with a reason. Then any red is new.
- Flow fixes (wave, ot-run, kit-rtl) get the front of each train by rule, as r123 did by hand.

## 8. Lane clones use the owner checkout as origin (added at COORD request, r124)

Measured:
- Clones under scratch2/claude with `origin = hub:OpenTallas`: epyc7 18, intel1 3 (+1 intel2:), epyc10 2. None
  sampled uses GitHub. `Host hub` is intel2; the path is /home/ubuntu/OpenTallas, the OWNER checkout.
- That checkout's main is 22c217df54. GitHub origin/main was fb7cf95840 at 09:16 and is b89ba8df4f0 now.
- It holds 4,765 branch refs. 68 claude/* refs have a commit dated today, pushed by lanes.
- Two cases today: S81-LEAF-T14 (bounce at 09:08, pushed tmp/s81t14-main-fb7cf958 there) and S81-SEAM-RST.
- MERGE-QUEUE-1 (10:02) made the queue clone take main from GitHub only. Lane clones are unchanged.

Root cause: no standard way to make a lane clone. Lanes copy an older clone, whose origin is the hub, and "origin/main"
then means a frozen main. The gate stamp records a sha but nothing checks that the sha is on the real main.

Structural fix:
- One helper, `ot-lane-clone <lane> <dir>`: origin = git@github.com:bojieli/OpenTallas.git, no hub remote,
  fetch, branch from origin/main. Lane briefs name it as the only way to create a clone.
- Queue gate: reject a READY when the stamp's main sha is not an ancestor of GitHub origin/main, or when the
  branch's merge base with origin/main is more than N merges behind (N = 20). The message names the helper.
- The owner checkout refuses pushes: `receive.denyAll`-style pre-receive hook, or remove the `hub` ssh alias path.
  This needs an owner-approved change to that checkout; I did not touch it.
- One sweep rewrites origin in the 24 existing clones (git remote set-url), with a list posted.

Owner: MERGE-QUEUE-1 (helper, gate, sweep). The pre-receive hook needs COORD and owner consent first.

## 9. Lane kills units by script

7 QC units (4 place, 3 gen) got signal 15 from `python3 -I /tmp/s4q2sw.py` at 08:0x, the S4q2 event switch.
ot-run reported the commands still running on epyc7/epyc10, so the rows failed while the work went on.
Root cause: the event switch is a private script. Fix: the switch is the one adoption command of class 5, which
re-keys or cancels rows through the wave, never with a signal from a lane shell. Owner: KIT-OPS-5.

## 10. Bookkeeping

- STALE 295 (S81 233: unowned 139). Nearly all are DEDUP or CANCELLED SUPERSEDED rows of old events, as at 0815
  (291). The 0815 fix (count only the current event) is not done. Live check NOT SEEN: intel2, epyc4.
- Repeat lines since 07:55: RETRY-IGNORED 913, DEDUP RELEASE 766, REAP-DEAD 112 = 59% of 3,023 lines.
  ARCHIVE FAILED 13.
- Queue stamps: 48 of today's posts carry an hour of 10-29 written before 10:00 PST (UTC hour with a PST label or
  a UTC label; DIE-QC-103 15, DIE-KV-ROUTE-1 6, also 7 RULING lines). 11 posts carry no time.
  Fix: lanes post only through bin/post.sh, which stamps the time itself; queue_view rejects a hand-written stamp
  that is in the future. Owner FLOW-HEALTH-1.
- Unowned in failure_breakdown: QC 3 cores and HBM 8 cores with no kit-wave row; S81 dsdv_gunit_l1f_bf no row.

## Did the 0815 fixes land, and did they work

| 0815 item | Landed | Worked |
|---|---|---|
| Merge flow-health-1 (preflight, class breaker, skew check, FLOW-HEALTH.tsv) | NO, 2 MERGE-FAILs | not live; fail ratio unchanged 0.73-0.93 |
| Supersede at adoption / old-plan block | oldplan-block merged 08:50 | yes in part: old-event RUNNING rows 21 -> 4 |
| Long-run watchdog | wave-longrun-1 merged 09:00 | in part: over-6-h openroad 76 -> 49 |
| epyc2 scratch choice or ot-store move | NO, MERGE-FAIL 08:59 | epyc2 admits by cleanup only, 64 GB over a 50 floor |
| alert-nonsticky | no merge found | unknown |
| epyc9 oversubscription | host choice not changed | epyc9 load 72 now; epyc7 is the hot host, load 143 on 96 |
| Closure manifest at adoption | NO | SRC-INCOMPLETE on the same S81 ROM file, 36 lines |
| Config drift alert | coord-commit prints PUSHED | HEAD = origin/coord/state at 10:04, only state file dirty |
| READY gate stamp | merged 08:31, bug fixed 09:56 | yes from the 10:00 tick |
| STALE counts current event only | NO | 291 -> 295 |
| Deny pushes into the owner checkout | NO | 68 refs pushed today (class 8) |

## Order of work

1. WAVE-COPYBACK: judge from rt/current, or re-judge every tick (class 1). It is the only class still burning P&R.
2. FLOW-HEALTH-1: get flow-health-1 green and merged (classes 5, 6, 10); then the 26 red baseline tests.
3. KIT-OPS-5: apply the r122 hold now; GENBUG-IMPL fixes the 2 red tests of kit-rtl-src-tree.
4. CLEAN-INTEL2-1115: hub scratch2 and root above 100 GB free. CLEAN-EPYC2-1115: epyc2-scratch3 test fix and merge.
5. MERGE-QUEUE-1: lane clone helper, base-on-origin gate, origin sweep (class 8).

## Not checked

- Whether each of the 49 long-running openroad processes is making progress. Only age and CPU share were read.
- The CPU share of class 1 rests on 4 sampled attempts (14-276 min, 2-8 threads), not on a full count.
- The after-fix false-fail rate: too few place completions on the new tree by 10:06.
- Clone origins were read on epyc7, epyc10 and intel1 only, two directory levels deep.
- localhost (rtx-pro) and epyc4 were not probed. S81-SEAM-RST's posts were not read; the case is as COORD stated it.
- `ot-run --status` prints "localhost REFUSED" for the hub itself (intel2), not for rtx-pro.
