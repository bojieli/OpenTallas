# FABLE-FLOW-0800: procedural and flow failure review (Fable, advisory, 11-18 07:40-07:55 PST)

Read-only review of 05:40-07:48 PST. Sources (intel2): autopilot/log.txt, autopilot/kit_wave.json + kit_wave_state.json,
lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py, `ot-run --status`, ~/merge-queue/log, lanes/posts/, df + load on epyc2/8/10/intel1.
No new holds, gates or approvals are proposed (r703/r704). Host rails stay (r709). No thread cap is proposed (owner).
"Share" = my estimate of kit-hours lost in the window (about 560 live kits); the counts are measured, the shares are estimates.

## Headline
- Launch starvation is gone. Fleet use 41% (05:49) -> 86-87% (06:56 on). Launches per hour: 8 (05:40-06), 377 (06), 136 (07 to :48).
  No SKIP-HELD, LAUNCH-HELD or pilot hold on the 4 non-HBM dies since 06:11. Rows not launching 150 = 104 running + 33 HBM (parked) + queue.
- The loss moved from "not launched" to "launched and failed as one class". Kit FAILs: 4 (05:40-06), 11 (06), 132 (07).
  118 of the 147 FAILs are 3 classes (65 + 30 + 12 + 11 re-fails); 8 are design.
- New hard problem: epyc2 scratch is under the floor (41-46 GB < 50). ot-run refuses epyc2, the rt sync fails with exit 4 on every commit
  since 07:43, and epyc2 is a tree host for S81, QC and HBM. epyc10 87 GB and intel1 77 GB are next.
- Tick is worse, not better: 379-1334 s (median 640 s). 8 ticks in 2 h.

## Fixes of this morning: did they take?
| fix | verdict |
|---|---|
| stops_off | TOOK for holds, pilot, dedup (48 DEDUP OFF RELEASE), cell limit (CELL-BIG "enqueued anyway"). Top-level `stops_off: true`, exclude hbm. NOT COMPLETE: BLOCKED-FLOW "same failure 3x" (7 rows), REPEAT-STOP (6) and CLASS-BREAKER open (11 lines, last 07:43) still print for S81 and QC. kit_wave_blocked.tsv is empty, so they may be report-only; the log does not say so. |
| SKIP-SAME-INPUT | NOT SEEN: 0 lines in 2 h. 21 REPEAT lines say "unchanged relaunch after a repeated failure" and the row launches. 15 S81 svc rows failed kit_rtl twice in the window with the same error after "RELAUNCH-ON-FIX: changed env". The input hash is too wide: it changes on env/overlay edits that do not reach the failing stage. |
| local supersede (norm_blocks) | TOOK as far as tested: 1 SWITCH-SUPERSEDE after 05:44 (06:17, "cancelling nothing this tick"). No plan apply with a renamed tree ran after it; unproven under a real apply. |
| signed check by normalized block (40c81dc321a) | NOT MEASURABLE: no signed type relaunched in the window; backfill lines are not logged. |
| stale-cancel rows not "in wave" (43346146e2) | PARTLY: pushed 07:06, rt carried it from about 07:15. Breakdown still shows cancelled (superseded) QC 9, KV 4 with no row; next tick decides. HBM 100 are excluded by design. |
| host lists from gen_hosts (cc9a312e650) | LIVE only since rt 07:37. 12 KV FAILs "die tree ... d22 missing on tolerant-swine" (07:01 x5, 07:42 x7): the place stage still landed on the hub, which has no kw45 tree at all. Judge on the 08:00 ticks; any further line means the pick does not use tree_hosts. |
| relocate_bind byte-exact restore + reset receipts | NOT TAKEN for QC: 13 FAILs "captured reset identity: bound reset emission source RTL identity differs" on 7 QC types (06:27-07:13), each failed twice; class breaker opened 06:27. |
| KW_RT_TOOLS classed INFRA | TOOK: FLOW "unclassified" at 07:01, INFRA at 07:42. Cause (above) is still open. |

## Classes, ranked by kit-hours lost

### A. One Tcl error kills a whole relaunch wave after 1-1.6 h - share about 12%
- Count: 65 S81 col_h9/h10 kits, all "resize.tcl: RESET v5 refuses empty explicit buffer set" at place. 65 launched in one tick (06:0x),
  failed 07:03-07:43. 11 were relaunched (07:0x-07:3x) on the same inputs and will fail the same way. Trend: new class, still growing.
- Root cause: the check is on kit inputs (an empty buffer list in the reset recipe) but runs inside the place Tcl, after synthesis and floorplan.
  The wave has no early stage that evaluates the recipe, so 65 kits spend about 80 kit-hours to report one config error.
- Structural fix: evaluate recipe hooks (reset buffer set, VPW, hook coverage) in kit_rtl/gen, where the kit already has the netlist view,
  so the class fails in minutes. And make the r705 skip real (class C) so the 11 re-fails cannot happen.
- Owner: S81-COL-FLOW-1118 (the error), WAVE-FLOW-R2 (early recipe check).

### B. Failed attempts leave live units for hours - share about 7%, and it inflates "committed threads"
- Count: 58 ORPHAN stops at 07:02-07:13 (epyc10 36, epyc8 17, epyc7 5), age 5.5-10.7 h, 553 unit-hours in total.
  Checked one: ot_s81sl_leaf__t31 attempt 8 was recorded FAIL at 21:16 on 11-17; its unit stayed until the next attempt existed, 9.8 h later.
- Effect: 36 units x 8 threads = 288 of the "849 committed threads" on epyc10 were dead attempts. The overload figure is partly bookkeeping.
  Whether they still burned CPU is not measured.
- Root cause: FAIL collection records the result and does not stop the attempt's unit; the orphan sweep only compares against a newer attempt.
  S81 had no relaunch for 10 h (auto_rearm), so nothing swept.
- Structural fix: the collect step that writes FAIL stops that attempt's unit in the same call (detached stop already exists).
- Owner: WAVE-FLOW-R2.
- Same family, still open from 0600: 6 S81 leaf jobs "kit busy (container: False, logs 404-516 min old); retry next tick", 36 lines (was 2 jobs).

### C. Unchanged or irrelevant-change relaunch - share about 5%
- Count: 30 FAILs on 15 S81 svc types ("reference net N_Y not structurally mapped", kit_rtl), each twice; 13 QC reset-identity FAILs, each type twice;
  6 KIT_INPUT_MISSING on 3 types; 287 RETRY-IGNORED lines for stale hand-added retry keys (noise, 144 QC keys are now redundant).
- Root cause: RELAUNCH-ON-FIX fires on "changed env / overlay" for the whole die. A die-wide env edit re-arms every FAIL row, including rows
  whose failing stage does not read it.
- Structural fix: per-stage input hash. A FAIL at stage S relaunches only when the inputs read by stages up to S changed. Delete dies.*.retry lists.
- Owner: WAVE-PILOT-FIX.

### D. Disk floor reached on tree hosts (rail, keep) - share about 5% and rising
- Count: epyc2 46 -> 41 GB (95%), REFUSED by ot-run; 43 containers still run there. FLEET-OPS-R forecast at 07:00 was "floor in 3.0 h"; it took 45 min.
  rt sync: "epyc2 FAIL 44/41 GB < 50; not copied", SYNC FAILED exit 4 at 07:43 and 07:46: epyc2 now holds an older rt than the other hosts.
  epyc10 87 GB (99%), intel1 77 GB (98%). UNDER-USE now counts 496 threads, not 624.
- Root cause: one tree per plan apply. epyc10 and intel1 hold 15+ src_head_pin_* generations, epyc8 20+ KV ones, epyc2 5 S81 ones; the 06:04 wave
  put 300 kits on the 3 S81 hosts. Cleanup deletes by idle age (24 h); trees of today are never idle.
- Structural fix: TOOLS-DECOUPLE phase 2 (one live tree + hard-link snapshots) for S81, KV and QC, as HEAD has since 06:47. Then a superseded
  snapshot with no live row is deleted at apply time, not by age. rt sync must treat a host under the floor as "skipped" (exit 0, host marked
  not launchable for new rt) instead of failing the whole sync.
- Owner: TOOLS-DECOUPLE (trees, sync exit), FLEET-OPS-R (free epyc2 now).

### E. Trees on too few hosts (overload) - share not separable from A/B
- Count: load epyc10 150-294/96, epyc8 115-180/96, epyc9 98-108/96, epyc2 125-186/128; epyc7 57/96 and intel1 72-83/112 have room; hub 4/112.
  Committed threads: epyc9 1344, epyc8 1095, epyc10 834, epyc7 404, intel1 334. gen_hosts: S81 = epyc8, epyc2, epyc10; HEAD = epyc9, epyc10; HBM = epyc2.
- Root cause: host choice follows where the tree is; the tree is copied by hand. With epyc2 refused, S81 has 2 hosts for 335 live rows.
- Structural fix: the apply step copies the tree to every gen host (hard-link snapshot makes this cheap), so memory admission alone spreads the work.
  Remove dead attempts (class B) before reading thread figures.
- Owner: TOOLS-DECOUPLE; S81-DIE-R3 for the epyc7 copy in progress.

### F. Wave tick length - multiplies every class
- Count: tick 645, 1179, 640, 379, 1334, 597, 528, 977 s. kit_wave_step 263-1084 s.
- Attributed: reap_dead 740 s (06:55), 386 s (07:37), 63 s; retry_enqueue 342 s (06:08); launch_safe 58-103 s; collect 20-78 s; plan_dies 6-131 s.
  poll_running 26-167 s and loop_gaps 50 s sit outside the step. Unattributed inside the step: 190-210 s on the short ticks
  (07:18: total 391 s, top ten 180 s). KW-STEP-TIMES prints only the top ten timers and no "other" line.
- Root cause: reap_dead probes hosts inline (the detached stop covers stops, not the liveness probe; one `docker inspect` of 20+ ids timed out
  at 120 s on epyc8 at 06:36). Loaded hosts answer ssh slowly, so the tick grows with load.
- Structural fix: one per-host snapshot (docker ps + unit list + df) taken once per tick in parallel and read by reap, collect, poll and under-use.
  Print an "other" timer so the 200 s is named.
- Owner: WAVE-FLOW-R2.

### G. Hand stop of a wave container, then misclassified - small, but wrong record
- Count: 1 (S81-GEOM-OPUS, epyc8, col_h9_r0_p2__t1__cl0045af7b__pv622a6f97, self-reported 07:23). The wave recorded it at 07:24:59 as
  "OOM kill; the resubmit runs with place memory x1.5". A hand stop (exit 137) is read as OOM.
- Root cause: private proof kits use the same container name pattern (dpkit-<type>-<pid>) as wave kits; OOM is inferred from the exit code alone.
- Structural fix: lane kits get their own prefix (the launcher sets it from the lane name), so a name can never match a wave job.
  OOM class needs the kernel/cgroup oom_kill counter, not exit 137.
- Owner: WAVE-FLOW-R2.

### H. Export and archive
- AUTO-EXPORT works per record (ARCHIVED-BOTH lines at 07:17-07:31). Backlog listed by AUTO-EXPORT-1118: s81 26, s81_head 44, kv 6 records still on fleet hosts.
- The old autopilot archive path still runs beside it: 5 "ARCHIVED ... (0 files, MD5SUMS) SIGNED-UNVERSIONED, not counted" for HEAD and
  1 "ARCHIVE FAILED 3054c87a89d6 (x18): probe rc 1: Traceback". Two exporters, one of them writing empty records.
- Structural fix: delete the autopilot ARCHIVE step; AUTO-EXPORT is the only exporter. Full DBs to AGIdock stay an owner call (space).
- Owner: AUTO-EXPORT-1118.

### I. STALE and unowned
- STALE 57, all HBM (parked; 9 unowned). S81 84 -> 0, KV 1 -> 0 since 0600. S81 state still holds 265 FAIL rows (history rows of relaunched items).
- 7 CONFIG-KEY-UNREAD keys (tools_refresh*), breaker_fix on 4 dies, pilot_mode, 60+ prev_*/only_items_prev_* blocks: dead config that lanes still read and edit.
- Owner: WAVE-PILOT-FIX (delete keys with the stop code).

## 0600 list: status
1. stops_off set + hub edits committed: DONE (43a71dd56c7, 8005cdea384). 2. Block sha without tree paths: DONE (norm_blocks), unproven under a real apply.
3. stops_off code default: DONE; deletion of pilot/retry_probe/breaker/dedup code: NOT DONE (lane declined bulk delete), residue seen in class C and the table.
4. S81 relaunch on rt tools: DONE (301 launches, tools_sha present). 5. rt smoke on a gen host + tools_refresh code deleted: DONE; config keys remain; phase 2 live tree: HEAD only.
6. kit_wave.json auto-commit + detached stops: DONE; the tick did not get shorter (class F). 7. KV only_items: NOT DONE (kv3_phy still outside).
8. "kit busy, no container" collected as result: NOT DONE (2 -> 6 jobs).

## Do now (ranked)
1. FLEET-OPS-R: free epyc2 scratch above the floor; TOOLS-DECOUPLE: rt sync skips a host under the floor instead of exit 4 (D).
2. S81-COL-FLOW-1118: fix the empty reset buffer set; no further col relaunch until then would be a hold, so make the 11 re-fails impossible through C (A).
3. WAVE-FLOW-R2: FAIL collection stops the attempt's unit; collect the 6 "kit busy" jobs (B).
4. WAVE-PILOT-FIX: per-stage input hash; delete retry lists, breaker/repeat code and their config keys (C, I).
5. TOOLS-DECOUPLE: live tree + snapshots for S81, KV, QC; apply copies to every gen host (D, E).
6. WAVE-FLOW-R2: per-host snapshot per tick, "other" timer (F); lane container prefix and real OOM evidence (G).
7. QC-FLOW-1118 / relocate_bind owner: 7 QC types still fail the reset identity check (table).
