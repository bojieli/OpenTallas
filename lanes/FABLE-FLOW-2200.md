# FABLE-FLOW-2200: procedural and flow failures, 19:43-21:47 PST

Reviewer: FABLE-FLOW-2200 (Fable). Read-only. Measured 2026-11-16 21:43-21:50 PST on hub intel2.
Sources: autopilot/log.txt 19:43-21:43 (1,156 lines, 22 ticks), lanes/FLOW-HEALTH.tsv (written 20:46),
tools/failure_breakdown.py (21:44), `ot-run --status` (21:43), df/load/kills.log on 6 build hosts (21:45),
merge-queue log + journal, origin/main (d1fa289b1cb), rt/current, lanes/posts since 19:50. Previous: FABLE-FLOW-2000.
Scope: process and tooling only.

## Headline

1. The merge service is down, so none of the fixes ruled after 20:50 is live. Last merge 20:50 (main d1fa289b1cb);
   one tick ran 20:52:53-21:45:59 and was stopped; at 21:47 the service is `failed` and the timer `inactive`.
   COORD posted this at 21:45 (MQ-PACK-FIX: 105,616 pack files). Eleven rulings are not on main:
   r412, r429, r430, r432, r434, r436, r437, r438, r443, r444, r445. Also not on main: publish gate 72c9b65,
   plan-job 664cf38, ingest --from-archive a5b3ca9, main-to-hub 9e6bc49.
2. So two "known" items in the brief are not true at run time. The wave does NOT read committed kit_wave.json:
   rt/current/tools/autopilot/kit_wave.py has 0 matches for the HEAD blob read. r437 is on no host's rt;
   S81 D5 carries it from the branch.
3. r429 can never merge as ruled. COORD ruled sha 8c7687c05761f8d5..., which is the sha of the FLEET-OPS-R post
   that was retracted at 20:24. The real head is 8c7687c0576b6e0f1c1416a3552a4ca342588c60; COORD.md has 0 lines
   with it. After the repack the queue will WAIT on it again. This is the fix for the epyc10 overload.
4. epyc10 scratch2 is filling now: 445 GB (20:30), 354 (21:05), 178 (21:40), 143 (21:46), about 240 GB/h.
   The 50 GB floor is about 25 min away. DISK-RATE alerted (21:40) but the alert has no actor.
   Other hosts at 21:45: intel1 88 GB, epyc7 119, epyc2 128, epyc9 145 (was 265 at 20:27), epyc8 371.
5. The wave almost stopped launching: 48 LAUNCH+ENQUEUE in 19:43-19:59, then 6 in 20:00-21:43.
   Fleet use: median 50% of 624 threads (range 41-63%), while epyc10 sits at load 141-156 on 96 cores.

## Kit wave by hour

| | 19:43-19:59 | 20 | 21 (to :43) |
|---|---|---|---|
| LAUNCH + ENQUEUE | 48 | 3 | 3 |
| FAIL | 1 (KV gen) | 34 (33 S81 kit_rtl, 1 KV gen) | 1 (KV gen) |
| LAUNCH-REFUSED same key | 2 | 5 | 0 |
| RETRY-IGNORED (stale attempt key) | 0 | 31 | 3 |
| SRC-INCOMPLETE | 0 | 11 | 11 |
| GEN-DISK-LOW | 0 | 6 | 0 |
| HUB-SYNC-FAILED | 0 | 2 | 2 |
| ALERT ADOPT-GUARD (hbm PLAN_MISSING) | 6 | 24 | 16 |
| TOOL-SKEW UNMEASURED s81 | 2 | 12 | 8 |

Tick time: median 162 s, max 528 s (2000: 167 / 535). Rows not launching: 55 (WAIT-FORM 25, q_running 14,
KW-FIX-45 8, SKIP-HELD 4, q_fail 2) plus 84 superseded-event rows. HOLD-AUDIT: HELD-BUT-LAUNCHED 0 on all ticks,
TERM-UNREACHABLE 44 on one tick (20:31) then 0, HOLD-SUPERSEDED 45 -> 72 (rising).
STALE current-event: 254 (2000: 257; 1900: 202). S81 304 rows, 203 FIX-S81-COL-STALE; QC 43; KV 10; HBM 107.
Unowned: 14 (KV 3, HBM 11). Live check NOT SEEN: intel2, epyc4 (epyc8 is seen now).

## Which 2000 fixes landed

| 2000 fix | State | Evidence |
|---|---|---|
| Approve cca8efdc426 (event_adopt matches plan event) | landed | r419, on main |
| Hold term refused at write time; dead-term audit | landed | r424 on main; HOLD-AUDIT prints TERM-UNREACHABLE; 46 records retyped 20:23 |
| QC Kf terms checked | landed | QC-PLAN-R 20:07, exact event names |
| Wait helper, no cmdline pattern | landed | r426 on main |
| Frozen views by content hash | landed | r427 on main; KV D10 built with it |
| DISK-RATE alert | landed, no actor | 16 lines since 20:30; nothing consumes them |
| epyc8 disk tonight | done | 377 -> 609 GB at 20:39 |
| Symlinked entry points | merged, not applied | r423 on main; /usr/local/bin/ot-heavy is still a regular file on 6 of 6 hosts (hash equal, 4b40ef39f849) |
| Wave reads committed config; patch command; lock owner | approved, NOT live | r434 not on main, not in rt/current |
| Publish gate (schema, PRE/G0, hashes, dry gen) | not merged | 72c9b65 GREEN, held for proof; run by hand it found S81 D4 not self-contained (21:18) |
| Plan priority by marker | not merged | 664cf38 GREEN, no ruling merged |
| Least-loaded gen host | not mergeable | r429 names the wrong sha |
| Self-heal at most twice | no | hbm PLAN_MISSING on 22 of 22 ticks; SRC-INCOMPLETE 22 |
| Skew check on a gen host | no | s81 UNMEASURED 22 of 22 ticks (fourth review) |
| Generated files out of the hub checkout | no | lanes/NOPROG.tsv caused 4 HUB-SYNC-FAILED; kit_wave_state.json dirty now |
| Fail on zero coverage; export read-back (HEAD) | not checked | |

Wrong in 2000:
- "epyc8 full near 23:00" was a straight-line guess from one burst (a 49 GB tree copy plus gate runs).
  FLEET-OPS-R measured +58 GB/h net at 20:16.
- "Place/CTS/route to the host with most memory" aimed at ot-run. ot-run already orders hosts by projected load
  (FLEET-OPS-R 20:15). The overload comes from the wave's gen-host choice and from trees that exist on epyc10 only.

## Verification of the items known since 20:00

| Item | Verified | Note |
|---|---|---|
| r434 wave reads committed config | no, not live | see headline 2 |
| r437 kitrtl rebase, D5 publishing | yes | S81-TYPES-R2 21:33: D5 = D4 + r437 + form B + plan sidecars, publishing on E8/E10 |
| r441 ingest --from-archive | branch only | a5b3ca9 not on main |
| Publish gate fails non-contained plans; D4 sidecars in a lane dir | yes | 18 SRC-INCOMPLETE lines on epyc8 name s81-b3-clk/run/b/B6gF2s4tapfix1 |
| oomkill branch gating | yes | two gates run at once on the same branch (3dfeac0 and 0dd62f9); the first is superseded |
| 20 guard kills in 24 h, all epyc10 | yes | 20 on epyc10; 2 since 20:00 (20:55 PST); other hosts 0 since 11-15 |
| E8 retirement raced the ingest | yes | FLEET-OPS-R 20:52; retire3.py refusal not read |
| Hub tools diverged from main | yes | 9e6bc49 READY 21:12, not on main |
| Stale retry keys | yes | 34 RETRY-IGNORED; kv3_hg_v1@1, @2, @4 against attempts 3-5 |
| Apply refused after checker sha moved | not seen in the log | consistent with r427 "identities re-key once" |
| tools-converge retire deferred | yes | RETIRE-SUPERSEDED retired 0 on 3 runs; kw45 holds 53 trees on epyc10, 44 on epyc9, 37 on epyc8 |

## Classes

Share = share of fleet thread-hours in the window, estimated.

### A. Fix pipeline stops silently (new; largest)

Count: 1 stall of 57+ min, 11 rulings and 4 READY branches waiting. Trend: new.
Root cause: the merge service is one serial oneshot with `TimeoutStartSec=infinity` and no progress alarm.
One unfetchable sha cost the whole tick; a partial clone with 105,616 packs made each lookup about 10 min.
A ruling is free text, so a retracted sha was ruled and nothing compared it with the branch head.
Fix (MERGE-QUEUE-1):
- The tick has a per-item time limit (2 min for fetch and lookup). An item over the limit is set aside and the
  tick goes on. A sha that is not the head of its branch is BOUNCED with one post, not waited on.
- No merge for 20 min with approvals pending posts one ALERT (the autopilot tick can check the log age).
- The repo is a full clone with `gc.auto` and a pack-count limit; the tick refuses to start above 200 packs
  and repacks first.
- COORD rulings are written by a command that reads the sha from the lane's READY line and checks it against
  the branch head.
Do now: re-rule r429 with 8c7687c0576b6e0f1c1416a3552a4ca342588c60.
Share: no compute of its own; it holds classes B, D and E open. About 50% of threads are idle behind it.

### B. S81 kit_rtl: paths outside the kit tree

Count: 33 FAIL in 11 min (20:10-20:21), 28 S81 types in the breakdown, 33 RESULT-RECLAIM refusals.
Trend: new at 20:10, stopped by the class breaker at 20:10:52 (worked; 1 probe failed at 20:15).
Root cause: a hold release (r414 retype) opened 34 types on a tree whose bind output names RTL in the bind
run's own lane dirs. Nothing ran one item of a held family on the current tree before the whole family opened.
Fix:
- (HOLD-FLOW-R) a hold that releases more than 5 items releases 1 pilot first; the rest follow its kit_rtl pass.
- (PUBLISH-GATE) the dry gen covers one item per kit class and fails on any path outside the tree. Merge it.
- (KITRTL-PATHS) r437, in D5.
Share: under 1% of compute (fails in minutes). 28 types (7% of S81) blocked 1.6 h so far.

### C. Trees and plans that are not self-contained

Count: SRC-INCOMPLETE 22 (2000: SRC-SYNC 13), SRC-SYNC self-heal 3 (654 and 82 files copied), ADOPT-GUARD
PLAN_MISSING 23. Trend: up.
Root cause: kit_wave.json may point at any absolute path. S81 asbuilt and plan sidecars live in
s81-b3-clk/run/b/... on epyc10; KV bind RTL in kv-r/hg2cgate. Other hosts are then "not a gen host", so the
die is pinned to epyc10. The self-heal copies files each time and never stops.
Fix:
- (PUBLISH-GATE) apply refuses a die block in which any path lies outside the published tree or the bind-of-
  record dir. The gate's sandbox mounts only those two.
- (WAVE-CONFIG) SRC-INCOMPLETE on the same host and die on 3 ticks posts one NEEDS-ACTION to the die owner
  and stops repeating. HBM PLAN_MISSING (44 alert lines, die parked) is silenced by a `parked` flag.
Share: this is the cause of class D. Direct cost small.

### D. epyc10 overload and guard kills

Count: load 141-156 on 96 cores on 22 of 22 ticks; CPU pressure 37%; 35 of 126 running jobs; 20 guard kills
in 24 h, 2 since 20:00. Four hosts sit at load 23-35. Trend: flat (2000: load 169-188).
Root cause: class C pins S81 and KV gen to epyc10, and the gen-host pick does not use load (r429 not merged).
ot-run counts 60 of 96 threads there while openroad uses 75 cores: declared threads are below real use.
Fix:
- (MERGE-QUEUE-1 / COORD) merge r429.
- (FLEET-OPS-R) FLEET-OPS-R copies every applied tree to at least 3 gen hosts in the apply step itself
  (KV D10 was done this way at 21:25; make it the rule in apply_reviewed_tree_marker.py).
- (FLEET-OPS-R) ot-run admission adds a load term: no new job on a host with load1 above 1.2 x cores while
  another host can admit it.
- (WAVE-CONFIG) the oomkill/INFRA_KILLED branch: a guard kill is not a design fail and does not use a retry.
Share: about 28% of jobs run about a third slower: near 10% of running throughput.

### E. Disk: alert without actor, superseded trees kept

Count: 16 DISK-RATE lines, 6 GEN-DISK-LOW, epyc10 -240 GB/h now. Trend: worse on epyc10, intel1, epyc7.
Root cause: (1) DISK-RATE only posts. (2) Each route job keeps 4-5 ODBs of about 2 GB (4.5-15 GB per job;
epyc9 wrote 134 GB in 90 min from ten jobs). (3) Each plan step publishes a new 49 GB tree per host and
the old ones stay: retire-superseded retired 0 three times.
Fix (FLEET-OPS-R):
- DISK-RATE under 1 h to the floor makes the wave stop new launches on that host in the same tick and
  starts the guarded cleanup. No lane action needed.
- The job deletes 5_route.odb, 5_3_fillcell.odb and 6_1_fill.odb when 6_final.odb is written and hashed.
- Apply writes superseded_trees for the die; retire runs through the delete guard in the same apply.
  Trees share unchanged files by hard link at publish (same filesystem), so a new tree costs its delta.
Do now: epyc10.
Share: none yet. A full epyc10 kills its 35 jobs (28% of running work).

### F. Retries on an unfixed cause (KV hg_v1)

Count: 3 identical gen fails (19:49, 20:5x, 21:22), 2 RELAUNCH-ON-FIX "changed tools", 1 REPEAT-STOP at 3.
Root cause: the fail key contains the stage-tool sha. Every rt/current sync changes it, so the same-key
refusal opens although the failing input (3 frozen views in D5) is unchanged. The same whole-tool sha
re-keyed every tree guard and refused an apply. Retry keys name an attempt number, so they go stale.
Fix (WAVE-CONFIG):
- The fail key uses the hash of the files the failing stage read (import closure of that stage), not the
  tool tree sha. Same for the tree guard: checker identity = hash of the checker's own closure.
- A retry names the fail fingerprint, not an attempt. It is consumed when that fingerprint is the latest.
- An INFRA @gen fail that names a tree input is released only by a tree switch.
Share: under 0.5%. Cost was KV: 0 new kits past gen until D10 at 21:28.

### G. Stale state, noise and small faults

- Hub checkout: generated NOPROG.tsv blocked sync 4 times; kit_wave_state.json dirty; six .state.json.<pid>
  and three STALLS.txt.tmp files left behind. (FLEET-OPS-R: move generated files out; write temp files in /run.)
- CONFIG-KEY-UNREAD 3: lanes keep backups (prev_gen_hosts_fleetopsr1116c/d) inside the live config.
  (WAVE-CONFIG: kit_wave_edit.py refuses unknown keys; backups are git history.)
- REAP-DEAD SILENT kv3_hub_C, 22 lines: the test wants 360 s of CPU growth per window, but the tick is
  about 280 s and the stage has one thread, so it can never pass. (WAVE-CONFIG: growth per elapsed second.)
- Two gates on one branch at once (oomkill). (MERGE-QUEUE-1: a new sha cancels the gate of the old one.)
- kills.log on epyc10 is in UTC, the hub log in PST. (FLEET-OPS-R: one zone, with offset.)
- Unowned 14 (KV 3 pv types, HBM 11). HBM is parked; the 3 KV types need an owner or a retire.
- HOLD-SUPERSEDED 72 and 84 superseded-event rows are not retired. (HOLD-FLOW-R: retire with the plan apply.)
Share: under 1% together.

## Order of work

1. FLEET-OPS-R: epyc10 disk now (143 GB, -240 GB/h).
2. COORD: re-rule r429 with the real sha. MQ-PACK-FIX: restart the timer; add the per-item limit and the
   no-merge alert.
3. After the queue runs: confirm r434 and r437 in rt/current; rule publish gate, plan-job, r441, main-to-hub.
4. PUBLISH-GATE + FLEET-OPS-R: no path outside the tree; 3 gen hosts per applied tree.
5. FLEET-OPS-R: DISK-RATE stops launches; intermediate ODBs deleted at result; superseded trees retired in apply.
6. WAVE-CONFIG: fail key by stage closure; retry by fingerprint.
7. HOLD-FLOW-R: pilot-first release for holds over 5 items.

## Not checked

- retire3.py SIGNED-not-in-store refusal (code not read).
- The refused apply after the checker sha moved (no log line found).
- HEAD zero-coverage and export read-back fixes.
- Who writes to epyc10 scratch2 (S81 D5 publish and route jobs are the likely writers; not measured).
- QC "other flow error 7", S81 "other flow error 7", S81 "no host 5": rows not opened.
- The idle 50% is partly intended: 203 S81 col types are stopped by S81-TYPES-R2 on purpose and HBM is parked.
