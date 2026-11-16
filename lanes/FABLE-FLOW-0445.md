# FABLE-FLOW-0445: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-16 01:46-02:25 PST on hub intel2 (all times below are hub PST;
the brief's clock times run about 2-3 h ahead of hub PST).
Window: autopilot/log.txt 23:45-02:13 PST (1,960 lines), lanes/FLOW-HEALTH.tsv (written 01:31), kit_wave.json (01:25
and 02:0x), kit_wave_state.json (01:54), kit_wave_tool_skew.json (01:52), tools/failure_breakdown.py (02:00),
`ot-run --status` (01:46), load/df on 6 build hosts (02:05), lane posts and rulings r252-r270.
Previous review: FABLE-FLOW-0015 (window 21:45-23:45). Scope: process and tooling only.

## Headline

1. The fleet is under-used and the cause is holds, not capacity. Launches fell from 190 to 45 in 2 h 25 min
   (KV 41, QC 3, HEAD 1, S81 0). Running jobs fell from 264 to 164; wave rows RUNNING from 118 to 26.
   Used threads are about 57-61% of 624. No disk or memory refusal occurred in the window.
2. S81 has launched nothing since 23:47 (2.5 h). It waits on a tree switch. The S81 tree was built twice
   (e594a73db756, then e4b9ae9f1c1f at 01:35) and no READY-TREE post exists at 02:10. Main moved 7 merges past
   the first pin in 75 minutes. The trees chase main and cannot catch it.
3. Three 0015 fixes worked: merge wait (24 merges, runtime synced 1 min after each), typed holds
   (TERM-UNREACHABLE 538 -> 21), KV launches (0 -> 41). Two did not: the DEDUP release loop (still 67 lines
   every tick) and the config-key reader check (not in the runtime).
4. The fail-key gate has a new hole: any change in a die's overlay releases every fail key of that die.
   KV got 41 RELAUNCH-ON-FIX; 12 of 39 fails were the same item failing with the same text.

## Kit wave, 23:45-02:13

| | this window (2 h 28 min) | FABLE-FLOW-0015 (2 h) |
|---|---|---|
| LAUNCH | 45 (KV 41, QC 3, HEAD 1, S81 0) | 190 |
| FAIL | 39 on 23 items (KV 26, S81 11, QC 2) | 32 on 28 items |
| same item, same text again | 12 (31%) | 4 (12%) |
| RELAUNCH-ON-FIX | 41, all KV (overlay 20, tools 13, both 8) | 5 |
| LAUNCH-REFUSED | 19 | 3 |
| ENQUEUE (place done) | 5 | 15 |

| Count | Die | Stage | Cause | State at 02:13 |
|---|---|---|---|---|
| 18 | KV | gen_lint | kit_rtl_paths rejected wave-staged copies of the kit's own sources (8 items, 2-3 rounds) | fixed by merge fa627e234cf (01:28); 8 items relaunched 01:14-01:33, none failed again |
| 12 | KV | gen | kv3_pv_v1/v7/v12: no RTL header for blackbox ot_qwen_tp8_pv_join_t; 4 identical rounds (00:52, 01:32, 02:12) | open; released each time by "changed overlay" |
| 1 | KV | kit_rtl | kv3_hub_C leaf qkd_ahub | fixed by kv-hubc-relview (01:16) |
| 5 | S81 3, QC 2 | pipeline | nested ssh timeout host to host on a snapshot copy (23:52, 00:03) | typedinfra merged 00:14; no transport event since, so the new typing is unproven |
| 8 | S81 | place | landing band 3, preflight 1, DPL-0033 2, GRTM 1, other 1 | design; owners named by fail_route |

## FABLE-FLOW-0015 fixes: did they land, did they work

| 0015 class | State | Evidence |
|---|---|---|
| 1 bind names its tree | worked for launches, structure not changed | KV 41 launches from 00:06. The QC bind for the pinned tree was made by rewriting the old path in .f/json by hand (TOOLS-CONVERGE 01:21). Relative paths + tree sha in the bind: not done |
| 2 config key with no reader | not landed | no reader check in rt/current tools/autopilot. The trees are rebuilt instead; QC switched at about 01:58 with 7 proof items; S81, HEAD, KV still on the old trees at 02:10 |
| 3 hold released only by a lane post | not landed, and it bit | HOLD-AUDIT has the same 4 counters, no OWNER-SILENT. QC tree READY 01:21, switch pushed about 01:58: 37 min inside the usage-limit stop |
| 4 ready branches wait | worked | 24 MERGED lines 23:12-01:58; runtime follows main in 1 min (merge 01:28, rt 01:29; current 0c49f5c6af19 on all hosts 02:00) |
| 5 fail key released by any tool change | landed for missing_input (00:26) | new form through the overlay, class 3 below |
| 6 infra typed as design | merged 00:14, unproven | reverse case now: the pv_join source fault is typed INFRA[tool_mix] |
| 7 serial launch | worked per launch, no gain in latency | launch 7.4 s -> 1.1 s (14 launches in 15 s). kit_wave_step 74-146 s (was 326-503). Ticks still start every 9-11 min |
| 8 health tables on old trees | worked | FLOW-HEALTH.tsv 01:31, SKEW lists the trees live at 01:07 |
| 9 rows with no terminal state | not working | 67 DEDUP RELEASE lines in every tick, 938 of 1,960 log lines (48%); 0 DEDUP-WAIT lines. ARCHIVE FAILED 3054c87a89d6 is at x9 |
| typed holds (HOLDGEN) | worked | TERM-UNREACHABLE 0 -> 506 -> 538 (typed terms in config before the code) -> 21 after merge 00:46. Left: QC 15, HEAD 5, S81 1; HBM 107 legacy keys not migrated |

## Summary, ranked by waste

| # | Class | Count | Trend | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Die tree carries a copy of the tools, so it goes stale at every merge | 9 full tree builds for 4 dies in 3 h; S81 0 launches 2.5 h; QC on 2 of 6 gen hosts | worse | most of the idle 40% of threads (class 2) | TOOLS-CONVERGE-1115 |
| 2 | Fleet under-used behind holds and a lane stop | used threads 57-61%; wave RUNNING 118 -> 26 | worse | about 40% of fleet threads idle | KIT-OPS-5, HOLDGEN-1115 |
| 3 | Overlay change releases every fail key of the die | 41 releases, 12 same-text repeat fails | new form of 0015 class 5 | under 1% CPU; 3 KV types looped 4 times | FLOW-HEALTH-1 |
| 4 | Switch steps need a live lane | QC switch 37 min late; S81 still held | recurs (third review) | part of class 2 | HOLDGEN-1115, KIT-OPS-5 |
| 5 | Rows with no terminal state | DEDUP 67/tick; 95 RETRY-INFRA rows, many 15-30 h old | same | none; hides real lines, inflates STALE | FLOW-HEALTH-1 |
| 6 | Fail-route posts per class per tick, also for closed classes | 52 posts and commits in 2.2 h | new | none; reader time | FLOW-HEALTH-1 |
| 7 | Tick period fixed at 10 min | 14 ticks in 2 h 28 min | same | fail detection up to 10 min late | KIT-OPS-5 |
| 8 | Hub checkout shared state | 2 HUB-SYNC-FAILED | same | posts late by 15 min once | MERGE-QUEUE-1 |
| 9 | Disk floors | 0 refusals | better | none | CLEAN-ALL-1115 |
| 10 | STALE and unowned | 190 current (+173 superseded); was 205 (+155) | flat | none directly | FLOW-HEALTH-1 |

## 1. The die tree carries a copy of the tools

Evidence. On epyc10: src_qc_pin at 90057d87f02c, 3d71c7911c34 (bind only) and e594a73db756; src_s81_pin at
e594a73db756 and e4b9ae9f1c1f; src_kv_pin at 0d0eec1e3a01, 7ce1e8344eb1 and fa627e234cf7; src_head_pin at
e594a73db756. Each is a git archive of main plus a data overlay, 323,733 files for QC. Main took 24 merges in
2 h 46 min. TOOLS-CONVERGE reports builds of 25 min and longer, slowed by epyc10 at load 113, where every
build runs. The QC replicate to epyc7/8/9/intel1 started 01:21 and was still copying at 01:55, so the wave
logs `SRC-INCOMPLETE epyc9 qwen_compute` every tick and QC gen runs on epyc10 and epyc2 only.
The skew gate cannot see this: for a pinned tree it reports `measured false, n_differ 0`, while main is 7
merges past the QC pin. The other dies read s81 68, s81_head 50, hbm 94, KV 16 of 227 modules, mode warn.
The brief adds that the gen switches default to off, so a new tree alone changed nothing; I did not verify
that, and it is the same fault from the other side: nothing proves that a key acts.

Root cause. Tools and die data ship as one tree. Every tool merge makes every tree old, and a full rebuild
plus a 300k-file copy to 6 hosts takes longer than the gap between merges.

Structural fix (TOOLS-CONVERGE-1115).
- The die tree holds data only: plan, bind, RTL, overlay, with a manifest hash. Kit tools run from
  rt/<sha>, which already reaches all hosts 1 min after a merge. The kit record stores the rt sha.
  "Tree lacks the code" and tool skew then cannot occur, and a tool merge needs no rebuild.
- Until then: build the tree on each host from its local git mirror (ot-git-mirror) plus the overlay
  archive (761 files for QC), verify by manifest hash. No host-to-host copy of the tree.
- The skew file reports, for a pinned tree, the count of closure modules that differ between the pin and
  main, not `measured false`.
- Effect proof replaces the reader check of 0015: after any die_gen_env change the first kit of that die
  must show the effect in a named output (PDN offset in pdn.tcl, tt_setup_repair.tcl ran in the log). The
  check is one script per key; a key with no script is refused at config load.

## 2. Is the fleet under-used: yes

| Host | load / threads | jobs | note |
|---|---|---|---|
| epyc2 | 21-30 / 128 | 12 | gen host for QC only (7 proof items); scratch2 135 GB free |
| epyc7 | 33 / 96 | 24 | root 120 GB under the 150 GB floor: only jobs with --dir on scratch2 |
| epyc8 | 56-60 / 96 | 31 | |
| intel1 | 67-76 / 112 | 27 | |
| epyc9 | 70-130 / 96 | 36 | |
| epyc10 | 116-119 / 96 | 34 | all tree builds, rsync sources, git (4 cores) |
| localhost | 3 / 112 | 0 | admits 786 GB; by rule no heavy jobs |

Used threads, capped at the host size: 356-378 of 624. All hosts admit 379-753 GB; earlyoom kills in 3 h: 0.
Causes, in order:
1. S81 (353 of 394 types unsigned) is under `hold_items "*"` tree_switch plus `route_hold_items "*"`:
   13 rows running, 79 ROUTE-HELD, 294 ENQUEUED.
2. QC (120 of 127 unsigned) runs 7 proof items by `only_items`.
3. HBM is parked; HEAD has 7 types left; KV runs 12 rows.
4. Jobs follow the tree. Trees are built on epyc10 and reach other hosts late, so epyc10 is at 1.2 x cores
   while epyc2 is at 0.2. ot-run orders hosts by load only among hosts that hold the inputs. S81 gen_hosts
   omit epyc2 and intel1; KV gen_hosts omit epyc2.

Fix (KIT-OPS-5): TOOLS-CONVERGE builds trees on epyc2, not epyc10. gen_hosts for every die = all 6 build
hosts; the wave already drops a host whose tree does not verify. One line per tick:
`UNDER-USE used/total threads, idle cause by die (held N, proof-only N, no tree on host N)`, and one
NEEDS-ACTION to COORD when used is under 70% for 3 ticks.
Fix (COORD ruling, not tooling): the S81 route hold keeps 79 placed kits from routing on the old PDN form.
Whether those routes are worth running is a design call; the process fact is 250 idle threads.

## 3. Overlay change releases every fail key of the die

kv3_pv_v1, v7 and v12 failed at gen with the same ValueError at 00:52, 01:32 and 02:12 (and gen_lint at
00:32). Each time the key refused the relaunch for one or two ticks (LAUNCH-REFUSED works) and was then
released as "changed overlay". The KV overlay is edited by two lanes in the window; the edits did not touch
the missing header. 28 of 41 releases cite the overlay.
Root cause: the key holds one hash for the whole die overlay.
Fix (FLOW-HEALTH-1): the key stores the hashes of the files the failed stage read (the kit file list is in
the attempt dir); it releases when one of those changes, or when the file named in the error appears. Same
rule for tools: only the import closure of the failed stage. Also type "no RTL header for blackbox" as
`FLOW[design:gen]`, owner the die lane, not INFRA[tool_mix].

## 4. Switch steps need a live lane

The usage limit stopped the lanes for about 1.5 h. QC: tree READY 01:21, config switch about 01:58. S81:
tree dir complete 01:35, no post, no switch. The steps are mechanical: verify manifest on gen hosts, set
src / bind_out / manifest hash / tools_sha, drop the hold, launch proof items.
Fix (HOLDGEN-1115 with KIT-OPS-5): a typed hold term `tree_ready:<die>:<manifest_hash>`, released by the
tick when `src_manifest verify` passes on at least 2 gen hosts; the switch itself is a file
`lanes/handoff/tree_switch_<die>.json` written by the builder and applied by a tool, so the autopilot can
apply it with no lane alive. The same form serves any hold whose release is a check a script can run.

## 5. Rows with no terminal state

DEDUP: every tick releases the same 67 S81 members: owner status CANCELLED with queue RUNNING 34,
ENQUEUED/FAIL 20, CANCELLED/None 10, FAIL/None 3. The 0015 fix parks a member only when the owner's fail
key blocks. These owners have no blocking key, and the die is under `hold_items "*"`, so the member cannot
relaunch and is released again.
Fix (FLOW-HEALTH-1): release is a state change, logged once: the member moves to PENDING (or HELD:<key>
when the die or item is held) and leaves the DEDUP scan. Test: two ticks on the same state print no line.
RETRY-INFRA: 95 rows (S81 55, HBM 20, QC 12, KV 8); the STALE list shows S81 rows in RETRY-INFRA for
15-30 h. Fix: a RETRY-INFRA row not relaunched within 2 ticks takes the name of what stops it
(HELD:<key>, SUPERSEDED, NO-HOST:<reason>).
ARCHIVE FAILED 3054c87a89d6: x9, a Python traceback in the probe. Fix (CLEAN-ALL-1115): after 3 identical
failures park the record and post once.

## 6. Fail-route posts

52 FAIL-ROUTE NEEDS-ACTION posts since 00:00, one commit each; it is the top committer in ~/coord. At 01:59
it asked KV-102 about class c59ba070b0 (gen_lint kit_rtl_paths, 10 items), which r267 closed at 01:11 and
whose items relaunched clean from 01:14. At 01:54 the lane installed its own unmerged fail_route.py as the
live copy.
Fix (FLOW-HEALTH-1 takes fail_route): a class closes by itself when every item in it has a later attempt
past the failed stage, or a COORD ruling names the class id; one digest post per owner per tick. Installed
tools come from rt/current only (TOOLS-CONVERGE-1115: add fail-route to the ot-tools-drift table).

## 7. Tick period

After fasttick the tick takes 149-226 s (7 ticks from 01:03), of which loop_gaps is a constant 60 s. The
timer still fires every 9-11 min, so a fail is seen up to 10 min late and a fix relaunches 10 min later.
Launch speed under a real load (100+ launches) is not yet shown; the largest tick had 14.
Fix (KIT-OPS-5): autopilot.timer OnUnitInactiveSec=120 (tick ends, 2 min, next tick); loop_gaps runs every
third tick.

## 8. Hub checkout

00:32 HUB-SYNC-FAILED: a non-log edit of lanes/posts/KV-102.md in the hub checkout. 01:22: pushes rejected 5
times because a pre-push deny hook meant for ~/OpenTallas applied to ~/coord through a shared hooks dir;
scoped at about 01:2x.
Fix (MERGE-QUEUE-1): each repo sets its own core.hooksPath; coord-commit.sh checks at start that a dry-run
push is allowed and names the hook if not. Posts go through post.sh only; the hub sync names the writer of
a non-log edit from the file's last post line.

## 9. Disk and admission

No GEN-DISK-LOW, DISK GUARD or NOT RUN line in the window. Standing: epyc7 root 120 GB (floor 150), hub
intel2 scratch2 94% used (206 GB free), epyc2 scratch2 135 GB, intel1 scratch2 227 GB. rt keeps a
2 MB manifest and a tree per synced sha (count of old ones not measured). The reaper cron still names epyc4.
Owner CLEAN-ALL-1115: prune rt to the shas named by live attempts; drop epyc4 from the cron line.

## 10. STALE and unowned

190 current-event (+173 superseded); 0015 had 205 (+155). Unowned: S81 199, QC 14, KV 8, HBM 11 (was 198, 11,
8, 11). Most S81 rows are DEDUP, SUPERSEDED or CANCELLED pv members from 11-14, which class 5 would name.

## Not checked

- Whether the first QC proof kits on the pinned tree show the die-phase PDN and TT repair (launched about 02:0x).
- The brief's statement that gen switches default to off.
- typedinfra on a real transport failure (none occurred after the merge).
- What the 164 running jobs are by kind (wave route against lane-private builds).
