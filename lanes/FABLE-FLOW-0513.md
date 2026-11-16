# FABLE-FLOW-0513: procedural and flow failures, ranked by fleet time wasted

Reviewer: FLOW-REVIEW-0513 (Opus; Fable at weekly limit). Read-only. Measured 2026-11-16 03:43-04:15 PST on hub intel2.
Window: autopilot/log.txt 01:43-03:45 PST (1,280 lines; 13 ticks), plus 11-13..11-16 for repeat streaks.
Sources: lanes/FLOW-HEALTH.tsv (03:33), tools/failure_breakdown.py (03:50), `ot-run --status` (03:50), loadavg/df on
6 build hosts (04:08), COORD rulings r271-r287, lanes/handoff/tree_switch_*.json. Previous: FABLE-FLOW-0445.
Scope: process and tooling only.

## Headline

1. The fleet is still 41% idle, and the cause is still the tree. Used threads (capped per host) are 368 of 624
   (59%), the same as at 0445. Launches fell again: 31 in 2 h (QC 23, KV 6, HEAD 2, S81 0); FLOW-HEALTH launches by
   hour went 19 -> 15 -> 7. S81 has launched nothing since 11-15 23:47 (4 h). QC launches went to a tree that now
   fails its own manifest check (cp -al hard links), so QC is stalled too.
2. Most 0445 fixes landed in this window: r278 (tree_ready term), r280 (#3 fail key by file, #5 DEDUP, #6 fail-route
   digest, config-key reader), r283/r286 (proof records cannot hold their proof items), r284/r285 (shared-inode
   check, delta-built v2 trees), r287 (2-min tick, UNDER-USE line, CPU-aware admission; merged 03:51, not yet seen
   running). DEDUP went from 67 lines per tick to 0 after 03:13. Fail-route commits went from 52 to 19 per 2 h.
3. Retries on causes that were never fixed now happen at the route level, not at gen. The wave's same-fail key
   and BLOCKED-FLOW (3x) stop repeats at gen and kit stages. Route outcomes (ot-run CLASSIFY) have no fingerprint.
   coll_n hit DRT-0255 on the same net (net25397) in the same routeBox (62700 653220) 6 times from 11-15 05:22 to
   11-16 00:12, with 8 route CRASHes in a row, and was relaunched again at 03:04 as attempt 21 ("changed
   overlay+tools"). hd_serdes had 5 post-CTS SETUP_TRIAGE stops in a row and was relaunched at 03:04; it was held
   by hand at 03:43. In this window 3 manual HOLDGEN stops (kv3_pv_*, kv3_pc, hd_serdes) did the work that a
   self-stop should do.
4. intel1 scratch2 has 36 GB free (99% used). At 0445 it had 227 GB. kw45 trees take 741 GB in 37 dirs. A
   third S81 pin tree (eb1e73448bd0) was being written there at 04:05.

## Addendum 05:35: the weekly-limit outage, 03:45-05:35

The lanes stopped. COORD posted one ruling (r288, 04:04). The autopilot ran 12 ticks (149-334 s, still about
every 10 min).
- 1 LAUNCH in 1 h 50 min (hd_ctl 04:43), 3 FAIL (2 QC SELFCONT on the comment path, class 5; 1 KV ssh 255 at
  place, INFRA), 9 LAUNCH-REFUSED. The fail keys and holds were correct and nothing acted on them. Every
  open class needs a lane edit, so an outage stops the fleet. This is class 1 plus class 3 seen from the other side.
- r287 reached the runtime by 05:27: the UNDER-USE line works. 05:35: `idle 332 of 624 threads (used 47%)`,
  epyc2 90 idle, epyc8 72, epyc7 71, epyc9 3. Rows not launching: 900, of which tree_switch 383,
  **enqueued_not_held 318**, PARKED-OWNER 56, WAVE-HOLDS 36, WAIT-FORM 25. Used fell 59% -> 47%; running jobs
  142 -> 116.
- New, worst: 318 rows are ENQUEUED with no hold and still do not launch. Nothing names their reason. Fix
  (KIT-OPS-7): UNDER-USE splits enqueued_not_held by the first launch gate each row fails (fail key, BIND-STALE,
  SRC-INCOMPLETE, no gen host with disk, CPU admission, dedup). Any row that is unheld and unlaunched for 3 ticks
  is a bug. It posts NEEDS-ACTION once with its gate.
- Retry on an unfixed cause, a new instance: kv3_pc_v1__cl23f6a148 and kv3_pc_v1__cl7f648944 were each killed by
  earlyoom 4 of 4 times (03:42-04:52) and resubmitted every time with `--mem 48 unchanged`. Both ended CRASH
  infra-oom at 05:22-05:24. Fix (in the REPEAT-STOP of class 3, owner FLOW-HEALTH-1): an OOM resubmit raises
  --mem to the measured peak x 1.25, or moves to a host with that much free memory. A second identical OOM goes
  to BLOCKED-REPEAT and is not tried a third time.
- Disk: intel1 scratch2 fell to 35 GB (04:23), then rose to 54 GB, with GEN-DISK-LOW on every tick. No prune ran.
- 05:32 ALERT ADOPT-GUARD PLAN_MISSING hbm: the HBM plan points at a lane-private path
  (`kit-ops-1/hbm_pEv11c/plan/die_plan.json`) that intel1 cannot read. This is the same lane-private-path class as
  the S81 `src`. Fix: the config load refuses plan and src paths outside the published roots (TOOLS-CONVERGE-1115).
- Self-running gap. The release paths that need no lane (r278 tree_ready, r280 fail keys, BLOCKED-FLOW) worked.
  None of them can produce a fix. For an outage, the useful automatic step is the class 3 ledger plus a NEEDS-LANE
  queue that the first lane to return reads first.

## Kit wave, 01:43-03:45

| | this window (2 h) | FABLE-FLOW-0445 (2 h 28 min) |
|---|---|---|
| LAUNCH | 31 (QC 23, KV 6, HEAD 2, S81 0) | 45 (KV 41, QC 3, HEAD 1, S81 0) |
| FAIL | 26 (QC 21, KV 4, S81 1) | 39 |
| RELAUNCH-ON-FIX | 16 (overlay+tools 6, block+overlay+tools 5, tools 5) | 41 |
| LAUNCH-REFUSED (same fail key) | 15 | 19 |
| BLOCKED-FLOW (3x auto) | 1 (slw_sc_v2) | - |
| manual HOLDGEN stops of repeaters | 3 | - |
| DEDUP lines | 609 (67/tick to 03:03, 6 at 03:13, then 0) | 67/tick |
| ticks | 13, 154-276 s each, every ~10 min | 14 |

| Count | Die | Stage | Cause | State at 03:45 |
|---|---|---|---|---|
| 10 | QC | kit_topology | native clock table resolved outside its base (absolute live path in iso manifests) | fixed by r281 (kit_snap finds the copy); FLOW-GUARD breaker opened 02:32, PROBE passed for 6 families 03:22-03:42 |
| 6 | QC | src_manifest | QC pin tree e594a73db756 has hard-linked files (nlink 2, cp -al), 21 findings | open; fail key refuses relaunch; v2 tree per r285 |
| 4 | QC | selfcontained | `SELFCONT pg_pair_cap.tcl MISSING /srv/.../drt0255-proof/tools/...`: the path is in a provenance comment on line 1 of the landed tcl, not a load | open; false positive of the checker, refused by fail key |
| 1 | QC | kit_topology | slw_sc_v2 bit_route per_bit needs leaf_um | BLOCKED-FLOW 3x (works) |
| 3 | KV | gen | kv3_pv_v1/v7/v12 no RTL header for blackbox pv_join_t (4th round) | STOPPED-HELD by hand 02:32 |
| 2 | KV, S81 | place | CLAND band | design |

## FABLE-FLOW-0445 fixes: did they land, did they work

| 0445 class | Landed | Effect in window |
|---|---|---|
| 1 die tree carries tools | partly: r284/r285 shared-inode check + delta-built v2 trees; r277 ext-source check | not yet. All four v1 trees fail tree_smoke_assert (r285). Tool skew still S81 69, HEAD 53, KV 20, HBM 95 of 228 modules; QC UNMEASURED (tree not readable on hub). A third S81 tree is being built. The data-only tree (tools from rt/<sha>) is not started |
| 2 fleet under-used | r287 at 03:51 (CPU-aware admission, UNDER-USE line) | not yet running. 59% used, same as 0445. epyc10 122/96 and epyc9 92/96, while epyc2 45/128, epyc7 29/96, epyc8 27/96 |
| 3 overlay releases all fail keys | r280 at 02:46 | partly: relaunches fell from 41 to 16. But a route-level failure has no "file the stage named", so the overlay/tools rule still applies (coll_n, hd_serdes at 03:04) |
| 4 switch needs a live lane | r278 + r286 (tree_ready typed term, tree_switch_<die>.json) | the mechanism is in; tree_switch_s81.json and tree_switch_head.json were written 03:31; the switch waits on v2 trees (smoke) |
| 5 rows with no terminal state | r280 | worked: DEDUP 67/tick -> 0 after 03:13; RETRY-INFRA-STOP named rows once (22 lines, NO-HOST / UNEXPLAINED) |
| 6 fail-route posts | r280 | worked: 52 -> 19 commits per 2 h |
| 7 tick period | r287 | merged 03:51, not seen yet |
| 8 hub checkout | no change | HUB-SYNC-FAILED again at 02:32 (lanes/NOPROG.tsv edited in place); OK again by 04:12 |
| 9 disk | no prune | worse: intel1 scratch2 36 GB free; GEN-DISK-LOW on intel1 from 03:23, epyc2 at 02:44 |
| config key with no reader (0015 #2) | r280 | worked and found one real case (proof_items before r283 reached runtime, 03:13). It also lists every `*_prev_*` history key of every die, so a real unread key is lost in the list |

## Summary, ranked by waste

| # | Class | Count, trend | Fleet share wasted | Owner |
|---|---|---|---|---|
| 1 | Wave tree is a copy of main; every fix needs a new tree | S81 0 launches 4 h; QC tree now fails its manifest; 3 S81 trees in 4 h; worse | most of the 41% idle | TOOLS-CONVERGE-1115 |
| 2 | Idle threads behind holds plus unbalanced hosts | 59% used, flat | ~41% of threads | KIT-OPS-7 (r287), KIT-OPS-5 |
| 3 | Route-level repeats with no fingerprint (unfixed cause relaunched) | coll_n 6x same net, hd_serdes 5x, sle_fe_v1 3x same net; 3 manual holds; new as a named class | ~2-3% of threads (one route run 1-2 h x 16 threads each) | FLOW-HEALTH-1 (new: REPEAT-STOP) |
| 4 | Tree disk: full copies per pin on every gen host | intel1 227 -> 36 GB free in 2 h; worse | none yet; next is gen refusals on intel1 | CLEAN-ALL-1115, TOOLS-CONVERGE-1115 |
| 5 | Checks that fail open or false-positive | bind preflight QC skipped 3x (ModuleNotFoundError kit_topology, "unknown = launch"); TOOL-SKEW UNMEASURED QC; src_overlay unreadable on epyc9 5x; SELFCONT on a comment 4x | small | FLOWGEN-1116, KITINPUT-1116 |
| 6 | Config history keys counted as unread | 5 dies, dozens of `_prev_` keys per tick listing | none; hides real findings | KIT-OPS-5 |
| 7 | Hub checkout written in place | 1 HUB-SYNC-FAILED (NOPROG.tsv); same | posts late once | MERGE-QUEUE-1, FLOW-HEALTH-1 |
| 8 | STALE / unowned | 149 current (+182 superseded); was 190 (+173); S81 unowned 193 | none directly | FLOW-HEALTH-1 |

## 1. The wave tree is a copy of main

Evidence. S81: trees e594a73db756 and e4b9ae9f1c1f (01:35) and now eb1e73448bd0 (being written on intel1 at 04:05).
tree_switch_s81.json (03:31) names e4b9ae9f1c1f with smoke PASS, but r285 says all four v1 trees fail
tree_smoke_assert (tt_setup_keep wiring, per-die RC scale), so a v2 tree is needed. QC: 23 launches on
src_qc_pin_e594a73db756; from 03:22 the kits fail `SRC_MANIFEST DRIFT ... hardlinked, nlink 2` (6 fails). The
QC tree became untrusted while in use. S81 still points the wave at a lane-private tree
(`/srv/.../s81-b3-clk/run/b/B6gG3b/src`, 69 modules behind main).
Root cause: unchanged from 0445. Each tool merge that a die needs means a new full tree and a copy to every host.
r285 cuts the cost (delta of 41-51 files) but not the cause.
Structural fix (TOOLS-CONVERGE-1115):
- Data-only die tree; kit tools from rt/<sha> (already on all hosts 1 min after merge). The kit records the rt sha.
  A tool fix then needs no tree at all. This is the only change that removes classes 1 and 4 together.
- Until then: a published tree is read-only by inode. `publish` runs the r284 links check and `chattr +i` (or a
  read-only bind mount) on the tree root; any later copy uses `cp -a --reflink=auto`, never `cp -al`. A tree that
  fails links or manifest moves to NOT-READY and the wave stops new launches on it in the same tick (not per item
  after a failed attempt).
- The wave refuses a `src` outside `kw45/` (lane-private run dirs), by config load check.

## 2. Idle fleet

| Host | load / threads (04:08) | jobs (03:50) | scratch2 free |
|---|---|---|---|
| epyc2 | 45 / 128 | 19 | 172 GB |
| epyc7 | 29 / 96 | 15 | 349 GB (root 119 GB < 150 floor: --dir jobs only) |
| epyc8 | 27 / 96 | 22 | 242 GB |
| epyc9 | 92 / 96 | 27 | 666 GB |
| epyc10 | 122 / 96 | 34 | 3.2 TB |
| intel1 | 79-107 / 112 | 25 | 36 GB |

Running jobs fell from 164 to 142. Rows held: S81 101 (tree_switch), HBM 77 (parked), KV 4. The brief's "epyc10
160-177/96" was not seen in this window; 117-122 was.
Fix: r287 (KIT-OPS-7) is the right fix for placement. Verify in the next window: UNDER-USE line present every
tick; no host above 1.0 x cores while another is under 0.5; launches per tick no longer capped. If S81 is still
under tree_switch at the next review, COORD should decide to run S81 on the e4b9ae9f1c1f tree with the v1 smoke
gap named, rather than idle 100+ rows for another tree cycle.

## 3. Route-level repeats with no fingerprint (the retry-on-unfixed-cause class)

Items with 5 or more consecutive same-class failures, 11-13..11-16:

| Item | Level | Streak | Same signature | Still relaunching? |
|---|---|---|---|---|
| qwen_compute/coll_n | route | 8 CRASH flow-error, 6 of them DRT-0255 on net25397 at routeBox (62700 653220) | yes, byte-identical net and box | relaunched 03:04 (attempt 21) on "changed overlay+tools"; then failed selfcontained; now fail-key refused |
| s81_head/hd_serdes | route | 5 STRUCTURAL post-cts-hold SETUP_TRIAGE | yes | relaunched 03:04 (attempt 7); held by hand 03:43 |
| qwen_compute/sle_fe_v1__cl8210183c | route | 4 CRASH; 3 DRT-0255 on u_cland_l9_eo_l9_wi_i/u_ring.dch[3] | yes | 9 submits; last 02:22 |
| qwen_kvsys/kv3_pc_v3 | gen | 28 INFRA same class | yes | stopped since 11-15 07:36 |
| qwen_kvsys/kv3_pc__cl254f2e73 | mixed | 28 attempts, causes differ | no single class | resubmitted 02:42 (attempt 28) to a gone tree; held by hand 03:43 |
| qwen_kvsys/kv3_pv_v1/v7/v12 | gen | 18-28 fails total, 4 rounds of one cause | yes | held by hand 02:32 |
| qwen_compute/slw_st_a_v2__cl9f076a5c | gen | 8 KIT_NOT_SELF_CONTAINED, 40 fails total | yes | not since 11-15 20:53 |
| qwen_compute/slw_fw_v1__clf51c11d8__clc7ddab13 | gen | 10 pruned bind worktree | yes | not since 11-15 06:08 |

Root cause. Two counters exist and neither covers this. The wave fail key (same inputs -> refuse) and BLOCKED-FLOW
(3x same wave-stage class) see gen and kit stages. Route outcomes come back through ot-run CLASSIFY as broad
labels (CRASH flow-error, STRUCTURAL post-cts-hold) with no fingerprint, and any overlay or tools change
releases them. A die overlay or tools change happens several times an hour, so the release is almost certain.
Items that fail with a different cause each time (kv3_pc 28 attempts) pass every same-class rule.

Generic self-stop (FLOW-HEALTH-1, new sub-lane REPEAT-STOP; KIT-OPS-5 wires it into the wave):
1. One per-item attempt ledger in kit_wave_state across both levels: attempt n, stage reached, fingerprint.
   Fingerprint = stage + normalized first error with the identifying object kept: DRT-0255/0206 -> net name and
   routeBox; post-CTS -> gate name and worst endpoint group; gen/kit -> exception type and the file or module named.
2. REPEAT-STOP: 3 identical fingerprints in a row -> state BLOCKED-REPEAT:<fp>. Release only when (a) a file in
   that item's own kit input list (the kit file list of the failing attempt: block RTL, plan block, stage tcl,
   tool modules in the stage import closure) has a different hash than in the attempt that last produced <fp>, or
   (b) a COORD/owner line `unblock <item> <fp>` names it. A die-wide overlay or tools change alone never releases.
3. NO-PROGRESS: 6 attempts within 24 h with no attempt reaching a later stage than the item's best -> state
   STALLED, whatever the classes. Same release rule. This catches kv3_pc-type items.
4. Each new BLOCKED-REPEAT or STALLED writes one NEEDS-LANE row (owner = family owner from fail_route; else a new
   Sonnet lane per OWNER rule) and, per the Fable-on-repeat rule, queues a Fable PD review. No line on the next
   tick if the state is unchanged.
5. Test: replay coll_n's 11-15/16 history -> blocked after the 3rd identical DRT-0255 (11-15 11:22), saving 3 route
   runs and the attempt-21 relaunch; replay hd_serdes -> blocked at 20:13.
This makes the manual HOLDGEN stop list for repeaters unnecessary.

## 4. Tree disk

intel1 scratch2: 3.4 TB of 3.5 TB used, 36 GB free (227 GB at 0445; ot-run saw 83 GB at 03:50). kw45 holds 741 GB in
37 entries, including kvgeom4/5/6 binds, src_kv_kvgeom6_pgL, src_kv_kvgeom7u, kv102t18_kvgeom7u, 5 old HEAD trees
from 11-13 and two HBM main trees. GEN-DISK-LOW on intel1 every tick from 03:23 (gen moves elsewhere; route jobs
there still write).
Fix (CLEAN-ALL-1115): keep a tree only while named by kit_wave.json, a tree_switch file, a queued or running
ot-run job, or a live attempt (24 h mtime rule stands). Run per host now on intel1. (TOOLS-CONVERGE-1115):
the builder deletes the tree it superseded on each host once no live attempt names it, as part of the switch.

## 5. Checks that fail open or false-positive

- `bind preflight qwen_compute skipped (unknown = launch): ModuleNotFoundError: No module named 'kit_topology'`
  3x: the preflight imports from a tree that does not have the module and then launches anyway.
- `TOOL-SKEW UNMEASURED qwen_compute: tree ... not readable` on the hub; `src_overlay: qwen_compute unreadable on
  epyc9; hold compares without it` 5x.
- SELFCONT flagged an absolute /srv path in a provenance comment (line 1 of pg_pair_cap.tcl landed from
  DRT0255-PROOF-1115) as a missing input: 4 QC kits failed, and the fail key now refuses them until the file changes.
Root cause: checks run where their inputs are absent and default to pass, or match text instead of loads.
Fix: (FLOWGEN-1116) a check that cannot run says UNMEASURED and runs on a gen host where the tree verifies; an
unmeasured preflight holds that die's new launches for one tick and posts once, not "unknown = launch".
(KITINPUT-1116) SELFCONT parses only source/load/open/file statements, ignores comments; the land step strips
or rewrites absolute lane paths in provenance comments so the false positive cannot recur. Release the 4 QC
fail keys (coll_n, slw_fw_v2, slw_st_b_v1 pv6ace3e48, slw_st_b_v2 pva66d0f22) when it lands.

## 6. Config history keys

CONFIG-KEY-UNREAD (r280) lists for every die keys such as `die_gen_env_prev_kitops2_er3`, `flow_tag_kw28`,
`die_max_inflight_prev_kw32`. Fix (KIT-OPS-5): move `*_prev_*`, `flow_tag_kw*`, `*_note_*` keys to
autopilot/kit_wave_history.json (or exempt a `_history` sub-object), so the reader check prints only live keys.

## 7. Hub checkout

02:32 HUB-SYNC-FAILED: `lanes/NOPROG.tsv` edited in place in the hub checkout (the noprog watchdog writes it).
Fix (MERGE-QUEUE-1 with FLOW-HEALTH-1): generated tables go to an untracked path (`state/NOPROG.tsv`) or through
coord-commit.sh. The hub sync then never sees a non-log edit from a cron.

## 8. STALE and unowned

149 current-event (+182 superseded); 0445 had 190 (+173). Unowned: S81 193, QC 10, KV 4, HBM 11. Most S81 rows are
DEDUP or CANCELLED pv members of 11-14 under the tree hold.
Note: autopilot/kit_wave_blocked.tsv on the hub is header-only (mtime 21:45) although the 03:22 BLOCKED line says
slw_sc_v2 was listed there; either the list is written elsewhere or not written. FLOW-HEALTH-1 to check.

## Verified from the brief

| Brief item | Finding |
|---|---|
| QC kit_topology clock-table class | yes, 10 fails 02:22-02:32; r281 fixed it; probes passed from 03:22 |
| proof:DRT0255 hold held its own kits (r283) | r283/r286 merged 03:08/03:48; the 03:13 CONFIG-KEY-UNREAD `proof_items` shows config arrived before code |
| one QC pick per tick | not seen as such in this window (QC launched 7+3 at 02:14-02:15); r287 removes max_launch_per_tick |
| full lane clones filled epyc2 | GEN-DISK-LOW epyc2 64 GB at 02:44; now 172 GB free |
| cp -al copies (r284) | yes: QC pin tree fails SRC_MANIFEST DRIFT nlink 2 from 03:22 (6 fails) |
| converged trees predate today's fixes | yes per r285; S81/HEAD switch files written 03:31, switch not done |
| kv3_pc 27x on a deleted tree | yes: attempt 28 submitted 02:42; held 03:43 |
| epyc10 load vs idle hosts | 117-122/96 vs epyc7 29, epyc8 27, epyc2 45/128 |

## Not checked

- Whether r287 (2-min tick, CPU admission) is running: merged 03:51, after the window.
- Wall time and threads of each repeated route run (estimated 1-2 h x 16 threads each).
- Where the wave writes kit_wave_blocked.tsv.
