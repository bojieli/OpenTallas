# FABLE-FLOW-1350: procedural and flow failures, ranked by fleet time wasted

Reviewer: FABLE FLOW (read-only). Measured 2026-11-15 13:49-14:03 PST on hub intel2.
Window: autopilot/log.txt 11:47-13:58 PST, `ot-run --status`, kit_wave.json (local and pushed), kit_wave_state.json,
failure_breakdown.py (13:57), NOPROG-TABLE.md (13:45), df / free / ps on 7 hosts, queue posts 10:50-13:56.
Scope: process and tooling only. Previous review: FABLE-FLOW-1200.

## Headline

1. The `--src-tree` class (1200 class 1) was not fixed for 2.5 h and has grown: 32 -> 118 fails. At 13:32 S81 was
   adopted onto B6gE, a tree known to lack the flag, and 50 S81 items failed in the first tick. The 13:54 tick
   launched 56 more S81 items on the same tree; the hold covers 3 of them. The 14:01 tick then logged 110 S81
   kit_rtl fails (outside the window table below). Total since 11:47: 228. The fix (KITRTL-FAIL-1115) has ETA
   about 14:35; until then every tick repeats this.
2. New finding: a signed type without a flow release tag is not counted and is launched again. Today 20 signed
   items, 18 relaunched, 60 relaunches. This is the 11-14 owner rule (count on the R-MINIMAL record alone) not
   applied in the wave.
3. Three structural fixes of 12:00 have no code yet: class key breaker, hub disk precondition, watchdog
   exclusion. FLOW-HEALTH-1 and WAVE-PREPNR-1115 have not posted since 08:3x.

## Kit wave, 11:47-13:58

| Window | FAIL | LAUNCH | ENQUEUE | FAIL/LAUNCH |
|---|---|---|---|---|
| 2 h | 120 | 212 | 36 | 0.57 |
| 12h | 35 | 61 | 25 | 0.57 |
| 13h | 78 | 203 (incl. LAUNCH-KEEP lines; 13:3x-13:5x S81 adoption) | 6 | - |

At 12:00 the 2 h figures were 84 / 101 (0.83). Launches by die: S81 136, QC 62, HEAD 12, KV 2.
Fails by die: QC 62, S81 54, KV 4.

| Count | Stage | Class | P | State at 14:00 |
|---|---|---|---|---|
| 63 | kit_rtl | `bind.py: unrecognized arguments: --src-tree` (B6gE/src 26, qc-s29-tree2 32, B6gsh/src_rel2 4, KV kvgeom6 1) | P | firing |
| 55 | kit_rtl | same failure, logged as "KW_ROAM kit_rtl: ran on X, outputs copied back to Y" | P | firing |
| 2 | place | KV clock-landing band | design | out of scope |

118 of 120 fails are procedural and they are one class. 76 distinct items failed. No ENOSPC, no false place
fail, no GEN_LINT LOCAL, no KIT_NOT_SELF_CONTAINED in the window.

## Summary, ranked by waste

| # | Class | Count | Trend vs 12:00 | Fleet share wasted | Owner |
|---|---|---|---|---|---|
| 1 | Wave passes `--src-tree` to a die tree's old bind.py | 118 fails, 76 items | 32 -> 118, rising; S81 joined at 13:40 | CPU under 1%; stops every fresh QC and S81 item at kit_rtl (S81 adoption of B6gE yields 0 new kits) | KITRTL-FAIL-1115 |
| 2 | Signed type relaunched: no flow tag -> "not counted" -> launch | 20 items, 60 relaunches today; 18 in this window | new finding | estimate 2-4% (60 full P&R attempts on signed types; durations not measured) | new lane SIGNED-TERMINAL-1115 (or KIT-OPS-5) |
| 3 | No-progress watchdog cannot fire | EXCLUDED 83 of 106 rows; 43 openroad over 6 h, 30 over 12 h | flat (81 of 110; 44) | about 8% | WAVE-PREPNR-1115 (silent since 08:33) |
| 4 | 3x block does not block; class breaker missing | 16 BLOCKED lines, kit_wave_blocked.tsv has 0 rows; cbn_q01__cldd6ea846 blocked at attempt 6, 9, 12 | open, second review | under 1% CPU; class 1 ran 2 h before a hand hold | FLOW-HEALTH-1 (silent since 08:3x) |
| 5 | Adoption does not test the tool on the new tree | 50 S81 fails in the first tick after the 13:32 B6gE adoption | was class 8; repeated | 1 tick of 873 s, 136 launches void | SRC-TREE-1115 (adopt_guard) |
| 6 | scratch2 at the floor on epyc7 / epyc8 | epyc7 120 GB (56 GB at 13:34), epyc8 153 GB | flat; epyc7 dropped out as gen host 9 ticks | 0 direct; one of four S81 gen hosts lost | CLEAN-ALL-1115 |
| 7 | Hub disk has no precondition | scratch2 165 GB, 96% (204 GB at 12:35); 128 rt trees (118) | no fail this window; falling 20 GB/h | 0 now | FLOW-HEALTH-1, CLEAN-ALL-1115 |
| 8 | Typed holds: data landed, tick does not read them | 477 hold_release_on entries on 5 dies; 0 references in kit_wave.py | half done | none | WAVE-HOLDS-1115 |
| 9 | Tick length | 873 s and 686 s on adoption ticks (285 s before) | worse | launches arrive one tick late | KIT-OPS-5 |
| 10 | Merge queue bounce on missing GATE stamp | 2 BOUNCE, both merged within 22 min; 0 MERGE-FAIL since 11:40 | improving | none | MERGE-QUEUE-1 |
| 11 | Bookkeeping | STALE 136 current (+106 superseded); S81 unowned 150; ARCHIVE FAILED 12 (same sha, 3rd review) | flat | none | FLOW-HEALTH-1 |

Closed since 12:00: S81 src incomplete on epyc8/9/10 (class 3 of 12:00), false place fail, hub ENOSPC burst,
GEN_LINT LOCAL. Config drift: none (local kit_wave.json equals origin/coord/state).

## 1. `--src-tree` against an old bind.py (third hour)

Measured:
- kit_wave.py line 5726 (rt/current 57db4f9d7f66) still passes `--src-tree` with no test. `grep -c -- --src-tree
  tools/die_plan/bind.py` is 3 in rt/current and 0 in all five die trees on every gen host: B6gE/src (md5 77db4409),
  qc-s29-tree2, B6gsh/src_rel2, KV kvgeom6_pgL, HEAD rp21z (md5 4bdbc141, the 06:00 daily copy).
- By 10 min: QC 4-7 per tick from 11:50 to 13:40; S81 1 per tick until 13:30, then 50 at 13:4x.
- KITRTL-FAIL-1115 confirmed at 13:56 that KW_ROAM and the argparse text are one class (the roam note is appended
  after the stage output and becomes the decisive line). This closes the "not checked" item of 12:00.
- Hold (13:41, pushed): QC 24, KV 2, S81 3 items. The S81 hold was taken before the 13:4x burst, so about 50 S81
  items are not held. 13:54-13:58: 56 S81 LAUNCH lines on B6gE src. 14:01: 110 S81 FAIL @kit_rtl, 1 BLOCKED.
- HEAD: 12 launches, 0 kit_rtl fails, although its tree also has 0 hits. Not explained; I did not read a HEAD log.
- Fix in work: the wave probes the tree; if the flag is absent it runs main's tools/die_plan staged in the kit
  (symlink farm onto the tree data). Trees are not edited. COORD r149 asked to install bind.py into the trees;
  the lane declined because the manifest pins tree content. The lane's form is the right one.

Root cause in the process: unchanged. The wave is main; the tool it calls is the tree's. The merge gate tests the
wave against main's tool only. In addition the class fired for 2 h (11:33-13:35) before any hold, because nothing
counts a class across items (class 4), and the adoption switched a die onto a tree with a known skew (class 5).

Structural fix:
- Now (WAVE-HOLDS-1115 or KITRTL-FAIL-1115, one config commit): hold S81 fresh launches until the fix merges.
  A die-level key (`*` with release lane_ready:KITRTL-FAIL-1115) is enough; running attempts past kit_rtl continue.
- KITRTL-FAIL-1115: land the probe plus main-tool form. Make main-tool-on-tree-data the only form, not a
  fallback, so that no later wave change can outrun a tree.
- MERGE-QUEUE-1: gate rule for tools/autopilot/kit_wave.py: a change in a command line that runs a tree tool
  needs a test against a tree fixture of the oldest live src_sha.

## 2. Signed types are relaunched (new)

Measured in autopilot/log.txt, 2026-11-15:
- 29 "ARCHIVED ... SIGNED-UNVERSIONED, not counted as signed off: no flow release tag carries this commit's flow"
  lines, 20 distinct items (S81 slice_station 14, QC su_l0 3, HEAD hd_mesh_e, hd_st_n4, hd_tile).
- 18 of the 20 got a KIT-WAVE LAUNCH after the sign-off: 60 launches. 42 of them before 13:32, on the plan the
  item was signed on. Examples: hd_st_n4 signed 01:23, launched 08:21, 08:29, 08:38, 09:05, 13:15 (now AUTO-GEOM
  FAIL on attempt 11); slice_station__t26 signed 04:24, launched 6 times; slice_station__t40__cl1ea9de02 signed
  13:02, launched 13:05.
- The 18 launches after 13:32 are on B6gE (new plan block). Whether B6gE changes these types I did not check; if
  the type block is unchanged, they are the same waste.
- The queue shows it as "provenance FAIL FLOW" events to the die owner, 3 lines since 10:00.

Root cause: autopilot.py line 2204/2214 writes signed.tsv only with src_commit + flow_tag, else unversioned.tsv.
The wave reads "not in signed.tsv" as "not done" and launches. The owner removed this gate on 11-14 (count on
the R-MINIMAL record alone; no commit / flow tag / re-sign). The count side may follow that rule; the wave's
terminal test does not.

Structural fix: one terminal test for the wave: an archived R-MINIMAL SIGNED record for (item, type block) ends
the item, with or without a flow tag. The missing tag becomes a row for auto_resign (it already lists
SIGNED-UNVERSIONED) and never a launch. On adoption, a signed item is relaunched only if its type block hash
changed. Today: hold the 20 items by name until the test lands. Owner: this has no lane; I propose
SIGNED-TERMINAL-1115 (Sonnet, kit_wave.py + autopilot.py, one test).

## 3. No-progress watchdog (unchanged)

NOPROG-TABLE 13:45: EXCLUDED 83, YOUNG 15, KEEP 3, PROGRESS 3, NO-DATA 2. All 83 say "plan priority job"; they
are kit P&R (kv3_hg, kv3_pv, hub, col). Five intel1 GRT jobs are 19.6-19.7 h old with best = last and are YOUNG
("series started inside the last 6 h"); epyc2 col_h9_r0_p2 is 23.8 h old, the same. The watchdog flagged 4 jobs
in 3 h (2 svc yosys, 1 LEC, cbn_q11 GRT). cbn_q11 was cancelled by its lane at 6.7 h after COORD asked.
openroad over 6 h: epyc2 12, epyc9 10, epyc10 8, intel1 7, epyc7 4, epyc8 2 = 43; over 12 h: 30.
WAVE-PREPNR-1115 last posted at 08:33 and has a new duty from r145 (SYNTH-MEM-STALL at 60 min); kit_wave.py
has 0 references to it.

Fix (as 12:00): exclude on the declared priority (unit environment), not on command text; evidence age since the
best value, bounded by process age, across series restarts; print the matched token. COORD: check that
WAVE-PREPNR-1115 is alive; if not, restart it from its packet with this item first.

## 4. The 3x block does not block; no class breaker

16 BLOCKED-FLOW lines in the window; autopilot/kit_wave_blocked.tsv holds the header only. cbn_q01__cldd6ea846:
BLOCKED at attempt 6 (12:13), 9 (12:44), 12 (13:13), 9 fails in 2 h. cbn_q00 x3, cbx_q10, sle_hc2 the same.
BLOCKED is a log line followed by a relaunch. No CLASS-HOLD line, no lanes/FLOW-HEALTH.tsv, no skew check on the
hub. flow-health-1115b is not on main (merges 09:00-13:55 read).

Fix (as 12:00, section 6): key = (die, stage, exit code, normalised first error line), counted across items;
3 items in 30 min holds the key for the die and posts one line. BLOCKED writes the row and stops the relaunch
until the owner clears it. KITRTL-FAIL's stable reason "kit_rtl tool skew" is the first key. COORD: FLOW-HEALTH-1
has been silent since 08:3x; restart it or give this to KITRTL-FAIL-1115 as its next item.

## 5. Adoption without a tool test

13:32 WAVE-HOLDS adopted S81 B6gE in one tick. ADOPT-GUARD raised 0 alerts: plan, sha and files were present.
The tree's bind.py (00:41 PST copy) lacked the flag the wave has passed since 11:10, and FABLE-FLOW-1200 listed
the class at 12:48. Result: 50 fails, a 873 s tick, a second 686 s tick with 56 launches.

Fix: adopt_guard runs the wave's own first three commands on the new tree for one type as a dry run (bind
report check, kit-rtl, kit_topology) on one gen host and refuses the switch on RC != 0. With main-tool-on-tree
(class 1) the test stays as a guard for data skew. Owner SRC-TREE-1115.

## 6-7. Disk

- epyc7 scratch2 120 GB (99%), memory 79 GB free of 1007; GEN-DISK-LOW 9 lines (56 GB at 13:34), so the wave
  dropped epyc7 as gen host. That part works and is self-stopping. epyc8 153 GB (98%), intel1 284 GB (92%).
- Hub: root 264 GB; scratch2 165 GB (96%), down 39 GB in 85 min. 128 rt/<sha> trees. No hub-disk test in
  kit_wave.py. At this rate the hub reaches the 10:35 condition in about 6 h.
- CLEAN-ALL-1115 last posted 11:5x ("20% not reachable under the standing rules"). No admission or disk refusal
  in the user journals of epyc7, epyc10, intel1 in the last 2 h; ot-run admits all hosts (epyc7 41 GB, 1 waiter).

Fix (as 12:00): hub free space below 20 GB = no launch + one ALERT; ENOSPC in run-item = retry the write, not
an item FAIL. rt trees: keep the ones a live run-item or unit references plus the last 5; the rest go (about
100 trees). Keeps per file list (src manifest), not per tree.

## 8. Typed holds

Landed 13:32-13:41: hold_release_on on all five dies (S81 255, HBM 107, QC 66, KV 47, HEAD 2); 7 signed HEAD
holds dropped; S81 holds 373 -> 255; all pushed. The values are text ("event_adopt:Event F" 216,
"lane_ready:DIE-QC-103" 14, ...). kit_wave.py has 0 references to hold_release_on, so no tick releases or lists
anything. 104 HBM entries read "lane_ready:DIE-HBM-101 (HBM parked)": fine while parked.
Next step for WAVE-HOLDS-1115: the tick evaluates event_adopt:<name> against the die's event and lane_ready:<lane>
against a READY line in the queue; entries older than 24 h without a true condition are listed once per hour.

## 9-11. Smaller items

- Tick: kit_wave_step+admit 755 s at 13:46 and a 686 s tick at 13:58, because launches are sent serially at
  about 4 s each. No tick ran between 13:26 and 13:46. Launch sends should be batched per host.
- Merge queue: 2 BOUNCE for a missing GATE stamp (hcparam-all-1115-3, die-route-abs-1); both merged within
  22 min. 20 MERGED and 2 MERGE-FAIL (both before 11:40) since 10:50. The `ot-merge-queue gate` habit is in use.
- STALE 136 current-event; S81 173 with 150 unowned, nearly all DEDUP / CANCELLED / SUPERSEDED col rows of 11-14
  that no one will run again. They should leave the STALE list when the row state is SUPERSEDED or DEDUP.
  Live check NOT SEEN: intel2, epyc4, epyc9 (epyc9 is new). No-row cores: QC 3, HBM 8, S81 dsdv_gunit_l1f_bf.
- ARCHIVE FAILED 12 lines, one sha 3054c87a89d6, every tick, third review. DEDUP 793 + RETRY-IGNORED 495 lines.
- Superseded-plan launches: SKIP-OLDPLAN 6, CANCEL-SUPERSEDED 11; no launch on an old plan found.

## Did the 12:00 fixes land

| 12:00 item | Landed | Worked |
|---|---|---|
| Class 1: wave calls main's tool, or probe | NO (branch claude/kitrtl-fail-1115, ETA 14:35) | class tripled |
| Hold on the class | 13:41, 2 h after the first fail | QC yes; S81 no (3 of about 53 items) |
| KW_ROAM = `--src-tree` | confirmed by the lane 13:56 | classifier fix in the same branch |
| S81 ROM / src copy on epyc8/9/10 | YES 13:36 (398 inputs, sha256 checked) | SRC-INCOMPLETE stopped 13:24; S81 restages go to epyc8/9/10 |
| Typed holds with release condition | data YES 13:32; tick logic NO | S81 373 -> 255 |
| HEAD signed holds, HBM superseded holds | 7 HEAD dropped | yes |
| flow-health-1115b: class key, skew check, FLOW-HEALTH.tsv | NO | class 4 open |
| Hub disk precondition | NO | no burst this window |
| Watchdog exclusion and evidence age | NO | class 3 flat |
| Adoption stages and verifies first | NO | class 5 repeated on S81 |
| src-tree-manifest rollout | merged 12:34; no die switched | - |
| Origin sweep of lane clones | not re-measured | - |

## Order of work

1. WAVE-HOLDS-1115 / KITRTL-FAIL-1115, now: die-level S81 hold on fresh launches until the kit_rtl fix merges.
2. KITRTL-FAIL-1115: merge probe + main-tool form; post the first passing launch per die.
3. New lane SIGNED-TERMINAL-1115: signed record ends the item without a flow tag; hold the 20 items meanwhile.
4. COORD: FLOW-HEALTH-1 and WAVE-PREPNR-1115 have been silent since 08:3x. Restart both, with class 4 and class 3.
5. SRC-TREE-1115: adopt_guard dry run of the wave's first commands on the new tree.
6. CLEAN-ALL-1115: hub rt trees (keep referenced + last 5); epyc7.

## Not checked

- Why HEAD passes kit_rtl with a tree that lacks the flag.
- Whether B6gE changes the type blocks of the signed slice_station items relaunched after 13:32.
- CPU time of the 60 signed relaunches; the 2-4% share is an estimate from the count.
- Whether FLOW-HEALTH-1 and WAVE-PREPNR-1115 agents are alive; I read only their queue posts.
- Progress of the 43 long openroad jobs; lane clone origins; localhost and epyc4.
