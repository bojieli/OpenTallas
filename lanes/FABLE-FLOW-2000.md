# FABLE-FLOW-2000: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 19:45-20:25 PST on hub intel2.
Window: autopilot/log.txt 17:45-19:45 PST (2,015 lines), lanes/FLOW-HEALTH.tsv (19:25), lanes/NOPROG.tsv (19:37),
kit_wave.json (4 revisions 17:51-19:47) + kit_wave_state.json (19:55), failure_breakdown.py (20:07),
`ot-run --status` (20:10), df/load on 7 hosts, queue lines 17:45-20:05 incl. r196-r211, rt/history.log.
Previous review: FABLE-FLOW-1800 (window 15:45-17:45). Scope: process and tooling only.

## Headline

1. 119 launches in 2 h (60 per hour; was 99 and 50). 72 fails, all 72 before P&R. About 35 of the 119 launches
   (30%) reached geom/place/route or its queue; was about 10 of 99 (10%). The gain is HEAD (21 launches, 0 fails,
   2 signed off) and QC (38 launches, 12 fails). KV: 0 launches (die hold, tree rebuild ETA 21:30).
2. S81: 60 launches, 60 fails, one class, 16 items. It is the same sdc_lint class as 15:45-17:45 (56 of 56). The
   16 items (14 slice_station, 2 serdes) were launched 2 to 5 times each. r198 (18:25) said to keep
   `slice_station__*` and `serdes__*` held until G3b; none of the 16 is matched by any S81 hold key in any of the
   four kit_wave.json revisions of the window.
3. Three r196 guards are now in the runtime and none of them stopped this loop:
   - retry key (in rt since 18:44): 0 `INFRA-KEY-REPEAT` lines against about 42 S81 same-cause fails after 18:44;
   - class breaker: opens now (6 opens), but it released the sdc_lint class at 19:15 on "preflight passes again";
     15 launches followed at 19:16-19:18 and all 15 failed;
   - hold by list: not applied to this family.
4. The bind.py patch install (18:11) broke `kit-rtl --kit` in 3 die trees on 5 hosts for 55 min (QC until 19:30).
   The patch was gated on main, where `import os` exists, and installed into trees where it does not.
5. Fleet at 20:10: epyc2 22/128, epyc7 47/96, intel1 76/112 threads loaded; epyc9 141/96, epyc10 127/96,
   epyc8 90/96. About 197 of 624 build threads idle (32%; was 28%). The hub scratch is 1 GB under its own floor
   (149 < 150 GB): `ot-run` reports localhost REFUSED.

Closed since 18:00: breaker blind to INFRA (r201), ot-run hub drift (SAME), noprog drift on 7 hosts (r205),
HEAD prepared-plan mismatch (prepare_check, used live for NF13a), HEAD stale closed views (r209 refusal),
yosys stdin hang in the gate (r200), merge queue (16 MERGED, 1 MERGE-FAIL in 2 h 15 min).

## Kit wave, 17:45-19:45

| 10-min bucket | 17:5x | 18:0x | 18:1x | 18:2x | 18:3x | 18:4x | 18:5x | 19:0x | 19:1x | 19:2x | 19:3x | 19:4x |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LAUNCH | 4 | 1 | 33 | 5 | 16 | 2 | 15 | 2 | 23 | 2 | 6 | 10 |
| FAIL | 1 | 0 | 0 | 1 | 15 | 3 | 21 | 5 | 5 | 2 | 15 | 4 |

2 h totals: LAUNCH 119 (S81 60, QC 38, HEAD 21, KV 0), FAIL 72 (S81 60, QC 12). FABLE-FLOW-1800: 99 / 88.
FLOW-HEALTH.tsv: hour 18 launches 72, fail before P&R 40, passes 9; hour 19 (to 19:25) launches 2, fails 5.

| Count | Die | Stage | Class | State at 20:10 |
|---|---|---|---|---|
| 60 | S81 | gen | sdc_lint: SDC clock window outside plan clock.tap_window (16 items; 2 to 5 launches each) | not held; CLASS breaker open since 19:33, half-open after 30 min |
| 11 | QC | gen | KIT_NOT_SELF_CONTAINED (6 items; slw_st_a_v2__cl9f076a5c 3 times, attempt 11) | breaker opened 3 times, released after 2 min twice; owner QC-SRC-CLOSE-1115 |
| 1 | QC | gen | WAIT-DEP hard landing evidence unavailable | plan input, 1 item |

Repeat launches: 54 distinct items for 119 launches, so 65 launches (55%) are repeats. 23 distinct failing items
for 72 fails, so 49 fails (68%) are repeats; was 46 of 88 (52%).

Stage reached (kit_wave_state, latest attempt per item started after 17:45, 58 rows): S81 gen FAIL 16;
HEAD place 6, geom/route 9, signed off 2, gen_lint 1 (4 of these cancelled as superseded by NF13a);
QC place 5, geom/route 6, resume 1, gen running 3, gen FAIL 2, stage not yet written 6.
P&R or its queue: 29 of 58 items; by launches about 35 of 119.

## r196 score

| r196 item | Landed | Works |
|---|---|---|
| (1) PLAN-GATE-PRE pre-bind check | READY 19:49 @49d68a21bd1, not merged | first use on the KV c1 tree gave a TOOLS false positive (KV-102 20:03: `sys.path.insert` import not followed) |
| (1) waiter-FAIL relay within 10 min | not seen: 0 PLAN-GATE-SILENT or relay lines | no |
| (2) retry key (tool, src, plan, class) | merged, in rt since 18:44 | no: 0 repeats detected, see class 1 |
| (2) class breaker counts INFRA | merged, in rt since 18:44 | half: 6 opens, 18 LAUNCH-HELD lines; wrong release rule and split keys, see class 1 |
| (3) per-family kit_rtl smoke before adopt | used live for HEAD NF13a (8 of 8 families) + prepare_check; branches approved r210 | yes for plan switches: HEAD 21 launches, 0 fails. Not applied to tool patch installs (class 2) |
| (4) plan-event holds from the event's item list | no; S81 keys 481 -> 480 | no: the r198 family is not in the list |
| (5) KV one-sha tree | c1 built from main 8989ba7b175, replicated; smoke pending | KV wave at 0 launches for 4 h 20 min |
| (6) epyc2 back in gen | QC gen_hosts only (18:20) | no: 22/128 loaded; 9 SRC-INCOMPLETE and 18 ADOPT-GUARD lines for the QC plan files missing on epyc2 |
| ot-run deploy, noprog drift | hub SAME, 7 hosts reinstalled | yes; FLOW-HEALTH.tsv of 19:25 carries no DRIFT section, so the hourly table does not show it |

## Summary, ranked by waste

| # | Class | Count | Trend vs 18:00 | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Known-failing class relaunched: three guards, none closes | 60 S81 + 11 QC fails; 49 repeat fails | same class as 18:00 (56), now 60 | about 60 gen runs of 9-18 min, under 1% CPU; it is all of S81's launch activity | FLOW-HEALTH-1 (key, breaker), WAVE-HOLDS-1115 (family hold) |
| 2 | Tool patch installed into die trees untested | 1 install, 15 tree copies + 6 QC, 55-80 min broken | new | not measurable from the wave log (0 FAIL lines name it); lane kit-rtl runs lost up to 80 min | KIT-OPS-5, TOOLS-CONVERGE-1115 |
| 3 | Idle hosts: die sources not on epyc2, KV at 0, S81 at 0 passes | 197 of 624 threads idle | worse (28% -> 32%) | 32% | KIT-OPS-5, KV-102, DIE-S81-92 |
| 4 | Plan gates blocked by process | S81 G3/G3b waiters restarted 18:50; QC S4q7f blocking; KV tree | open | S81: 40 of 394 types signed off, 101 held for the event | PLAN-GATE-PRE-1115 |
| 5 | Config change re-arms every failed row | 33 launches at 18:17-18:19, 6 min after a die_gen_env default change (inferred from timing) | new reading | 16 of the 33 were the S81 class | FLOW-HEALTH-1 |
| 6 | Count/archive and hub sync fail every tick | ARCHIVE FAILED 12 lines (one job, 3054c87a89d6); HUB-SYNC-FAILED 9 lines; count ingest failing since 11-12 | open, 3 days | no CPU; the count is stale | new COUNT-INGEST lane on localhost; FLOW-HEALTH-1 |
| 7 | Hub scratch under its floor | 146-149 GB against 150; localhost REFUSED | worse (161 at 18:00) | hub cannot take ot-run jobs | CLEAN-ALL-1115, MERGE-QUEUE-1 |
| 8 | Hold table | S81 480 keys, 2 per col type; QC 49 after two edits in 2 min (19:45, 19:47) | flat | none directly | WAVE-HOLDS-1115 |
| 9 | Owner labels name dead lanes | BLOCKED line 18:23 "owner DIE-QC-101"; STALE S81 unowned 192 | worse (186) | none; posts go nowhere | WAVE-HOLDS-1115 / KIT-OPS-5 |
| 10 | No-progress table advisory | 3 SLOW, 0 NO-PROGRESS of 153 | better (6) | about 1% (col_h10_r1__t1 GRT 20.7 h on two hosts) | FLOW-HEALTH-1 |
| 11 | Log noise | DEDUP 804 + RETRY-IGNORED 481 = 64% of 2,015 lines | new reading | none; it hides the 72 FAIL lines | FLOW-HEALTH-1 |

## 1. A known-failing class is relaunched through three guards

Measured, item s81/slice_station__t6__cl54a9ceeb: LAUNCH 18:18, FAIL 18:33, LAUNCH 18:36, FAIL 18:54,
LAUNCH 18:55, FAIL 19:04, RETRY-RELEASE 19:04, LAUNCH 19:05, FAIL 19:23, LAUNCH 19:25, FAIL 19:43. Five
launches, one error text, plan B6gE@1510a6a72050 and src unchanged throughout.

Why each guard let it through:

- Hold. `fnmatch` of the 16 launched items against S81 hold_items at revisions cec756ef, c94b2ab5, c4b88543
  and HEAD: 0 of 16 held. The keys are per item (slice_station__t49, __t24__cl64811a5d ...); there is no
  `slice_station__*` or `serdes__*` key. r198 item (2) was not applied.
- Retry key. `infra_key()` hashes `rt_tools_digest()` with src, plan and class. The rt tree changed 7 times
  between 18:44 and 19:57 (82b7e71d, 774e4650, 81b2a1df, 45f9e3cc, 5aa7a65b, 537df0bd, 13568fb2), so a merge of
  any tool gives every failed row a new key. Also the key is consulted only while the row is RETRY-INFRA; a row
  that used its infra attempts ends FAIL and comes back through RETRY-RELEASE or the fresh-launch path, which do
  not read the key. State at 19:55: infra_seen has exactly 1 key per S81 item; infra_posted is empty.
- Breaker. (a) `norm_class()` masks digits but not the `__cl<hex>` suffix, so one error is 12 class keys
  ("slice_station__tN", "slice_station__tN__clNaNceeb", ...). The breaker opened at 18:54 for 6 plain-named
  items; 10 other items of the class launched at 18:55. (b) Release rule: "preflight passes again for every
  held item". The preflight does not run sdc_lint, so it passed: release 19:15, 15 launches 19:16-19:18, 15
  fails. KIT_NOT_SELF_CONTAINED: opened 18:53, released 18:56; opened 19:23, released 19:24; open again 19:43.
  (c) The die|stage CLASS breaker opened only at 19:33, holds 0 items by its own line, and half-opens after
  30 min.

Structural fix (FLOW-HEALTH-1, one branch):
- Key the retry on the inputs the failing step reads: (die src tree digest, plan sha, kit input digest of the
  item, class). Leave the hub rt digest out; the failing tool is the die tree's sdc_lint, not the hub runtime.
- Check the key at every launch path (RETRY-INFRA, RETRY-RELEASE, fresh launch after FAIL), in one function.
  A row whose key failed once is not launched until one member of the key changes. No timer, no half-open.
- A breaker releases on a changed key only. Remove the preflight release for classes the preflight does not
  test (pf_kind() == ''). Mask `__cl[0-9a-f]+`, `__pv[0-9a-f]+` and the type name in norm_class.
- Replay test: the 17:45-19:45 log must give at most 16 S81 fails (one per item) and at most 6 QC.
With the key in place the per-item hold is not needed for this class. Until it lands, WAVE-HOLDS-1115 adds the
two family keys of r198 today (release on G3b adopt).

Class 5 belongs here: at 18:11 `OT_TT_SETUP_REPAIR=both` became a die_gen_env default on four dies; 33 launches
followed at 18:17-18:19, among them the 16 S81 items whose gen cannot be changed by a P&R variable. Not proven
from code; the timing fits the "inputs equal" rule being cleared by the env change. Fix: the relaunch digest of
a row that failed at stage X covers only inputs read up to stage X.

## 2. Tool patches installed into die trees in place

Sequence: wave-prepnr-1115 @696e60ae77d, GATE pass 75/75 on main. The die-source patch was installed at 18:11
into S81 B6gE/src, KV kvgeom7u and HEAD c327 on epyc7/8/9/10/intel1, and into the QC tree on 6 hosts. bind.py
in those trees has no module-level `import os` (main has it at line 48); `kit-rtl --kit` raised NameError.
Found 19:06 (r207), fixed by copy+mv; QC fixed by 19:30; test added (r208). The lane's own post: "my earlier
check was wrong".

Wave exposure: 0 KIT-WAVE FAIL lines and 0 of 6,274 attempt logs of the last 4 h contain NameError. S81 fails
earlier at gen, KV was held, HEAD passed kit_rtl through its own wrapper. The loss was in lane-run kits and is
not in the log.

Root cause: the gate proves a patch against main. The trees differ from main in 35 to 72 of 227 modules (SKEW
19:07: S81 62, KV 72, HEAD 41, QC 35; cross-host copies identical). A patch that is correct on main is an
untested program on each tree. This is the fourth of this kind today (`--src-tree`, KV tool mix,
sdc_lint vs gen_phys, bind.py os).

Should "patch die trees in place" be banned: yes.
- From now: no hand edit and no patch file applied to a live die tree. A tool change reaches a die in one way:
  a new tree directory built from one sha (`make_src_tree`, as KV-102 does for c1), the adopt_guard per-family
  kit_rtl smoke on two hosts run against that directory, then the wave `src` pointer moves in one commit.
  The old tree stays for running jobs. adopt_guard exists and worked for NF13a; apply it to `src` changes as
  well as plan changes. KIT-OPS-5 owns the rule.
- TOOLS-CONVERGE-1115 is the end state (tree = main tools + plan). Its launch check is READY (20:02,
  @e4e05059f8e). Caution for the install: all four dies differ from main today, so the check must go in with
  the per-die allowlist filled or in `warn`, else it stops every launch. The allowlist must expire per die with
  the next tree build, not by date.
- tool_skew.py should also digest each tree per tick and post once when a live tree's digest changes without a
  `src` commit. That makes an in-place edit visible within one tick whoever does it.

## 3. Idle hosts

ot-run 20:10: epyc2 admits 675 GB, load 22/128; epyc7 684 GB, 47/96; intel1 364 GB, 76/112; epyc8 90/96;
epyc9 141/96; epyc10 127/96. No admission refusal on a build host in the window. epyc2 is in QC gen_hosts only
("the other die srcs do not exist on epyc2"), and for QC the plan of record and manifest files of treeA are
missing there: SRC-INCOMPLETE epyc2 9 lines 18:24-19:46, ADOPT-GUARD PLAN_MISSING/FIX 18 lines. Disk on epyc2
is no longer the cause (155 GB free after the two clone moves). epyc7 scratch2: 148 GB, 99%.

Fix (KIT-OPS-5): replicate each die's tree and plan inputs to all six build hosts as one step of the `src`
switch in class 2 (owner rule: never pin), and add the host to gen_hosts in the same commit only when the
adopt_guard check passes on it. Adding a host to gen_hosts first and staging files per SRC-INCOMPLETE line is
the per-instance pattern of FABLE-FLOW-1600 class 2 again.

## 4. Plan gates

S81 G3/G3b waiters were stopped and restarted at 18:50 with a new release list; QC S4q7f bound and was found
blocking by review; KV c1 is not yet smoked. plan_gate_pre.py is READY but not merged, and its TOOLS check has
one known false positive. PLAN-GATE-PRE-1115: fix the import resolution, merge, and deliver the waiter-FAIL
relay as a separate small branch today; the relay does not depend on the checker.
The r199 order (review in parallel with bind) is in use and found three blocking items before adopt.

## 6. Count, archive, hub sync

- ARCHIVE FAILED 3054c87a89d6 "probe rc 1: Traceback": 12 lines, once per tick, one job. No backoff, no owner.
- HUB-SYNC-FAILED: 9 lines; hub checkout dirty since 19:02 (lanes/COUNT-DIRECT.tsv, lanes/NOPROG.tsv,
  tools/release_tree_plan.py edited in the hub checkout).
- Count ingest: failing hourly since 11-12 (no AGIdock key on intel2); move to localhost in progress.

Root cause: a periodic job that fails prints the same line each tick; nothing counts consecutive failures.
Fix (FLOW-HEALTH-1): one table lanes/CRON-HEALTH.tsv from the job logs: job, last success, consecutive
failures, last error. A job with 3 consecutive failures is posted once with its owner. This would have shown
the count ingest on 11-12. Tools are never edited in the hub checkout; generated tables (NOPROG.tsv,
COUNT-DIRECT.tsv) are written by coord-commit only.

## 7. Hub scratch

intel2 scratch2 146-149 GB free, 96%; floor 150; localhost REFUSED. Writers (CLEAN-ALL 20:1x): mq1 worktrees
8 trees 9.9 GB + repo 8.9 GB, one rt tree per runtime change (0.4 GB each, 61 pruned = 26.3 GB), closed kits.
Fix: MERGE-QUEUE-1 moves all gate worktrees to the remote runner hosts (lanes still gate in the shared mq1
repo sometimes; refuse a gate in mq1 from any lane but the queue). rt keeps the last 5 trees not named by a
running process. Closed kits go to epyc10 (4.5 TB free).

## 8-11. Holds, owners, no-progress, log

- Holds: S81 480 keys; QC 50 -> 42 -> 49 in two commits 2 min apart (a lift and its correction). MHOLD tool
  (r210) is approved; route all hold edits through it, with a dry run that prints the items matched.
- Owner labels: still the dead lanes at 18:23 (census item 13). One field per die in kit_wave.json; KIT-OPS-5
  sets it in the same commit as a successor line. STALE 191 current (+155 superseded), was 174; S81 unowned
  192; QC unowned 10, KV 8, HBM 11.
- NOPROG 19:37: 153 jobs, SLOW 3: col_h10_r1__t1 GRT 20.7 h on epyc7 and 20.5 h on epyc10 (one type on two
  hosts, last log write 2.6 h ago); cbn_q01 pregrt_ff_hold 3.1 h without a log line. Rows still go to no
  lane. REAP-DEAD SILENT native59: 12 more lines.
- Log: print DEDUP and RETRY-IGNORED once per item and state, not per tick (1,285 of 2,015 lines).

## Does a class recur because fixes are per-instance

| Class | Per-instance steps in this window | One structural step |
|---|---|---|
| S81 sdc_lint | breaker per name, release, reopen, CLASS breaker; holds per item | retry key on step inputs, checked at every launch path |
| Tool skew | bind.py os fix by hand on 15 + 6 tree copies | new tree from one sha + smoke + pointer switch |
| epyc2 | host added, then files staged per alert | replicate + guard, then add |
| QC KIT_NOT_SELF_CONTAINED | 3 breaker opens, attempt 11 | QC-SRC-CLOSE restage of the 33 types; same retry key |

## For COORD, in order

1. WAVE-HOLDS-1115 now: `slice_station__*` and `serdes__*` on S81, release on G3b adopt (r198 item 2).
2. FLOW-HEALTH-1: retry key without the rt digest, checked on all launch paths; breaker release on key change
   only; cl/pv masking; replay test on 17:45-19:45 (class 1).
3. KIT-OPS-5: no in-place patch of a die tree; tool changes by new tree + adopt_guard smoke + `src` switch;
   replicate to six hosts before gen_hosts (classes 2, 3).
4. MERGE-QUEUE-1: tools-converge-1115 with allowlist or warn first; plan-gate-pre after the false positive fix.
5. PLAN-GATE-PRE-1115: waiter-FAIL relay as its own branch today.
6. FLOW-HEALTH-1: CRON-HEALTH.tsv (class 6); NOPROG rows to owners; log dedup.
7. CLEAN-ALL-1115 + MERGE-QUEUE-1: hub scratch above 150 GB; no lane gates in mq1.

Not checked: the code path that relaunches a FAIL row after RETRY-RELEASE (read only the key block, lines
8392-8520 of kit_wave.py); whether the 18:11 env change is what released the 33 rows; lane-run kit-rtl losses
from the bind.py install; the traceback text of ARCHIVE FAILED; the count ingest move; how many lanes gated in
mq1; owner_lane values after 18:23.
