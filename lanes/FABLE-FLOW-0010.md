# FABLE-FLOW-0010: flow and procedural review, 21:43-23:55 PST 11-17 (Fable)

Read-only. Sources: autopilot/log.txt (1,672 lines in the window), failure_breakdown.py (23:45), ot-run --status (23:46),
kit_wave.json + kit_wave_state.json, tools_refresh_*.log, lanes/handoff/tree_switch_*.json, per-host df / timers / rt/current,
FABLE-FLOW-2200, LATENCY-1117. Window totals: LAUNCH 189 (s81 90, KV 67, QC 19, HEAD 13), KIT-WAVE FAIL 86,
LAUNCH-HELD 157, LAUNCH-REFUSED 38, REPEAT-STOP 0. Fleet: 624 threads, about 1,250 thread-h in the window; UNDER-USE
reported 31-63% used (mean about 54%). Waste shares are estimates against real load, not declared threads.

## Verification of tonight's fixes
| fix | result | evidence |
|---|---|---|
| r680 stale fail_keys drop | works | FAIL-STALE dropped lines at 22:4x and 23:4x (9 fail_keys, 7 fail_sigs) |
| r680 breaker at 3 | works for new classes | HOOK_COVERAGE opened 22:45 on 3 fails; kit_rtl class opened 23:00 (7 fails landed in one tick) |
| r680 probe window | NOT bounding launches | see A: VPW class in PROBE since 21:49, 56 col launches followed |
| r684/r686 auto-clean timers | work | ot-auto-clean.timer (user unit) active on intel1, epyc2/7/8/9/10; last run 23:31, next 00:00 |
| r687 marker VPW key | works for new launches, 8 doomed jobs left | see A |
| r687 marker re-apply each tick | NOT fixed as a class | see B: gen_host / gen_hosts still re-applied each tick |
| r689 wave disk cap | works | gate:disk_wait 14-20 rows from 22:56; the last "No space left" place fails are 22:59 |
| r691 heavy-reap rotation | works | kit_wave_step 1,187-1,367 s (21:51-22:42) -> 176-490 s (23:02-23:42) |
| r693 optimistic publish_apply | works | QC N3 applied 23:38, ADOPT-ROWS 23:46 (LATENCY ETA was 01:15) |
| r685 S81 refresh hcparams | passes the overlay check | 23:35 s81 pass composed _t6433206 (22:19 and 22:45 passes were OVERLAY-PRIVATE) |
| tools_refresh on, 4 dies | config true on all 4; applied on 1 of 4 | see C |
| KV gen_env_outside_allow | works | 31 refusals 22:50-23:19, then 31 KV launches 23:2x; file md5 identical on the 4 KV gen hosts |
| hd_lep0N hold | works | failed 23:23, held 23:25, LAUNCH-REFUSED 23:29 |
| ORPHAN enforce (2200 E) | works | 2 "ORPHAN stopped" on epyc8 after 2 ticks of "would stop" |

## Tick times
kit_wave_step+admit: 1,212 / 1,187 / 1,367 / 627 s (21:52-22:56), then 190 / 186 / 333 / 491 / 400 s (23:03-23:42).
Tick total 265-601 s. Shorter by about 3-4x, but still 4.5-10 min, and rising again (190 -> 400-490 s).
- KW-STEP-TIMES top-10 sums to about half the step (23:41: 387 s total, about 200 s listed): about 190 s is not attributed.
- Largest named parts: plan_dies 40-104 s, collect 18-72 s, reap_dead 10-85 s; loop_gaps is a fixed 48 s every tick.
- Fix: print the unattributed remainder as its own field; cache plan_dies by plan sha. Owner WAVE-PILOT-FIX.

## A. Stale die-wide env relaunched through an open class: OT_S81_VPW_BANK (55 fails, was 20; rising, now tailing off)
- 55 FAIL "OT_VPW_BANK needs exactly two real VP SRAM macros, got 0" on col_h9/col_h10: 22:1x 2, 22:4x 28, 22:5x 4, 23:0x 6,
  23:1x 5, 23:2x 4, 23:3x 6, plus 1 after 23:43. 56 col_h launches in the window (21:48 14, 22:13 18, 22:37 9, 22:52 4,
  23:01 5, 23:07 3, 23:39 1).
- Three stacked process causes:
  1. Breaker: the class was RELEASED to PROBE at 21:49 ("the die's inputs changed: one item per family may launch"). The
     cause is die-wide, the probe budget is per family, and col has dozens of pv/cl families. State now: n 53, state
     "probe", probes 2, probes_failed 2. Two failed probes did not shut the class.
  2. The key moved to item_env at 22:15, but the tree-switch marker wrote it back each tick 22:44-23:06 (r687 fixed 23:16).
  3. Retries copy the old spec env (FIX-S81-VPW 23:08). Removing a die key does not invalidate a spec.
- Still live at 23:55: 8 of 12 RUNNING col attempts (started 22:5x-23:07) have `"OT_S81_VPW_BANK": "1"` in spec.json and
  will fail at global place. The 23:39 launch (col_h9_r0_p5 pvb22875c0 a5) has no key: the fix holds for new launches.
- Structural fix: (1) probe budget is per CLASS (3 in total); any failed probe shuts the class until the fail key's own
  inputs change. (2) die_gen_env key set is part of the spec digest; a removed key supersedes every queued or running
  attempt that carries it (SWITCH-SUPERSEDE on env, same as on tree). (3) carried from 2200 B: the tool decides
  applicability at gen.
- Do now: stop and relaunch the 8 doomed attempts (S81-TYPES-R3 / FIX-S81-VPW).
- Owner: WAVE-PILOT-FIX. Waste: about 10% of real fleet load (55 place jobs, 0.5-1 h each).

## B. Tree-switch marker is re-applied every tick (class of r687, still open)
- `dies.s81.hold_records` id s81-route-tree-01 keeps a `tree_ready:` term that is always true, so
  hold_records.apply_tree_switches merges lanes/handoff/tree_switch_s81.json into the die in memory on every tick.
  TREE-SWITCH s81 "switched gen_host, gen_hosts" was logged at 23:22, 23:34 and 23:45, after the fix.
- Effect now: marker gen_host epyc8, gen_hosts [epyc8, epyc2, epyc10, intel1] override derive_gen_hosts (23:07:
  epyc9, intel1, epyc7, epyc10, epyc2), which had dropped epyc8 for GEN-DISK-LOW (28-45 GB < 60). SUBMIT 23:41 still
  generates s81 leaf kits on epyc8.
- Risk at the s81 tools refresh: tools_refresh re-keys the term to the new tree, but the marker file still carries the
  old tools_sha, src_sha, queue_src and kit_rtl in `config`. They would be written back each tick. UNVERIFIED until the
  s81 refresh applies; check the first tick after it.
- Likely side effect (UNVERIFIED): the per-tick config flip changes the die input digest, which is what releases breaker
  classes to PROBE one or two minutes after they open (kit_rtl class: open 23:00, release 23:01 and 23:02).
- Structural fix: a marker is consumed once. Apply writes it to kit_wave.json and records the marker sha in state; it
  re-applies only when the marker sha changes. Host lists never come from a marker (derive_gen_hosts owns them).
  tools_refresh rewrites or retires the marker in the same commit as the switch.
- Owner: WAVE-FLOW-R2. Waste: under 1% direct; it is a cause of A and of F.

## C. Tools refresh after 23:15: applied on HEAD only
| die | passes in window | state at 23:55 | TOOLS-LAG 23:45 |
|---|---|---|---|
| s81_head | 21:55 APPLIED, 22:19 COMPOSE-FAIL (intel1 59 GB < 70), 23:13 APPLIED, 23:35 APPLIED (_t6433206) | applied | 23 commits (r685..r695) |
| s81 | 22:19 and 22:45 OVERLAY-PRIVATE; 23:35 composed _t6433206 | replicating for 20 min, not applied | 194 commits (r600 on) |
| qwen_kvsys | none between 21:02 COMPOSE-FAIL (epyc8 49 GB < 70) and 23:35 | replicating for 20 min, not applied | 1,003 commits |
| qwen_compute | enabled 23:28; 23:35 pass refreshed the tree that N3 replaced at 23:38 and COMPOSE-FAILed (epyc2 50 GB < 70); 23:45 pass on N3 | replicating, not applied | 1,006 commits |
- Root causes:
  1. Replicate is serial per host and all-or-nothing: a 47-55 GB tree takes 4-8 min per host, 20-30 min per pass.
  2. Main gains about 9 rulings per 10 min, so every pass is behind when it lands (HEAD applied 23:35, lag 23 by 23:45).
     Every ruling triggers a refresh, including autopilot-only rulings (r684, r686, r689, r691, r693) that no kit uses.
  3. A structural exit (COMPOSE-FAIL, OVERLAY-PRIVATE) stops the die until its tree changes: KV had no pass for 2.5 h.
  4. The epyc2 replicate check measured a 58 GB filesystem (epyc2 root is 99% full), while kw45 lives on scratch2 (223 GB).
- Structural fix: (1) refresh only when the missing rulings touch files a kit reads (path filter on the tree's tools
  manifest); (2) replicate to all hosts in parallel and apply on a quorum, with gen_hosts = hosts that hold the tree;
  (3) the disk check uses the filesystem of the target path; (4) end state from 1300/2200 D: kits read tools from
  rt/current and the tree pins rtl + plan only.
- Owner: WAVE-FLOW-R2 (1-3), LATENCY-R (4). Waste: no thread time; it keeps s81/KV/QC kits on tools without tonight's fixes.

## D. Failure class mis-keyed as INFRA: s81 svc kit_rtl "closure failed" (13 fails, new)
- 21:55 4, 23:00 7, 23:1x 1, 23:35 1. Types svc_hi/svc_lo dsdv_svc_rs, svc_pvso_entry.
- Real error (hub kit_rtl.live.log): `ValueError: reference net 673_Y not structurally mapped` in
  tools/die_plan/s81_svc_memory_closure.py port_source. It is a tool/design content error, not host or source skew.
- It is keyed INFRA[tool_mix], so it took the INFRA retry path: 4 fails at 21:55 did not stop 7 relaunches at 23:00.
  The class opened 23:00, was released at 23:01 and 23:02, a probe failed 23:35, and it is shut now.
- The gen host's attempt logs/ dir is empty; only the hub copy has the traceback.
- Structural fix: an exception raised inside tools/die_plan/* with a design-data message keys as FLOW/design with the
  inner exception text (ValueError line), never INFRA; "preflight passes again" cannot release a class the preflight
  does not exercise.
- Owner: WAVE-PILOT-FIX (keying); S81-TYPES-R3 (the closure error itself, needs a lane). Waste: under 1% (kit_rtl stage).

## E. Disk and admission (flat; epyc2 root still open from 2200 H)
- epyc2 root 99% (57 GB): protect_sources write failed 22:14 ("No space left"), QC refresh COMPOSE-FAIL 23:35,
  WORKROOT-ALT every tick. epyc2 is the idlest host all window (load 24-36 of 128).
- GEN-DISK-LOW work_root: intel1 1 GB (22:48), epyc10 10 GB (22:20), epyc8 28-45 GB (23:00-23:07).
- 3 place fails "No space left on device" (22:59; gen hosts epyc2, intel1) and 2 "no host qualifies" where the only
  candidate listed was localhost (scratch 144 GB < floor 150). localhost is REFUSED now (128 GB).
- scratch2 97% on epyc7, epyc10 and the hub (intel2 129 GB free; the hub has no ot-auto-clean timer).
- UNDER-USE idle is mostly supply, not admission: rows not launching 131 = q_running 44, WAIT-FORM 25, disk_wait 17,
  q_signed 16, q_fail 10. Declared threads are 5-9x cores (epyc8 841/96 at load 62), so thread counts say nothing.
- Fix: epyc2 root cleanup now; a place submit never offers a single-host candidate list; hub cleanup timer.
- Owner: FLEET-OPS-R. Waste: about 2% (5 fails, 17 disk_wait rows, epyc2 half idle).

## F. Self-heal that reports success and heals nothing (26 + 3, falling)
- SRC-SYNC "229 missing input file(s) copied epyc9->epyc2" for qwen_compute at 23:14, 23:26, 23:36. At 23:47 the target
  dir kw45/qcbind_pin_eb1e73448bd0_s4q9n1b/bind_s29q103S4Q9N1BBR does not exist on epyc2.
- ITEM-SYNC rc=2 x26: intel1->epyc9 qc-collcore-reset-1117/bind_L2BQ_rawall (9 items), epyc9->epyc2
  tl-qcphysdb/por/plan_s29_qc103_phyb.json. 4-5 per 10 min before 22:40, 1 per 10 min after 23:00. Same as 2200 E.
- HEAD: ALERT ADOPT-GUARD PLAN_MISSING on epyc10 at 21:54. The refresh tree was APPLIED while one gen host lacked
  4 files (source_plan.json, bind.py); SRC-SYNC healed it 2 min later.
- Structural fix: a heal verifies the target after the copy; two passes with no effect drop the host from the die's
  gen_hosts and post NEEDS-LANE. Backoff keyed by (src, dst, rc). Replicate verifies the manifest before "APPLIED".
- Owner: WAVE-PILOT-FIX. Waste: under 1%. Re-check after N3: the n1b bind path should no longer be asked for.

## G. Standing errors with no owner
- `AUTO-RESIGN PRESTAGE skipped: KeyError: 'tag'` on every tick (12 in the window, since 20:49, now 3 h). 2200 G, unfixed.
  Owner FLEET-OPS-R.
- HOLD-AUDIT: TERM-UNREACHABLE 80 -> 64, HOLD-SUPERSEDED 72-73, HOLD-ZERO-MATCH 15, **PILOT-DEADLOCK 0 -> 4 since 22:54**.
  No log line names the 4 items and no NEEDS-LANE row was written (0 NEEDS-LANE lines in the window).
- PLAN-CONFIG-DRIFT KV: 31 only_items match no plan item; kv3_phy and kv3_phy_v1 are outside only_items and never
  launch. HEAD: item_env hd_host matches no item.
- QC: 8 holds auto-released at 23:45 as "EXPIRED: owner lane QC-PLAN-R3 silent > 6 h (8.1 h)". The lane committed
  kit_wave.json at 22:34, so the silence test reads only one channel. Possible hold leak; UNVERIFIED. N3 superseded the rows.
- Structural fix (2200 F, not built): each audit counter above zero writes one NEEDS-LANE row per die with the item
  names; lane activity = any of post, commit or kit_wave edit.
- Owner: WAVE-PILOT-FIX.

## H. Stale, unowned, superseded (flat)
- STALE current-event 114 (2200: 114): S81 4 (FAIL-S81-1, 33 h), QC 9 with **4 unowned** (3 kit_rtl FLOW from 06:21,
  17.4 h; same rows as 1900 and 2200), KV 1, HBM 104 (parked).
- S81 "kit input missing" rows: 51 (2200: 48). Still not counted STALE.
- Superseded-event rows 74 -> 98 after the QC N3 adopt; RETIRE-SUPERSEDED retired 0 on every pass.
- Fix: as 2200 I. A superseded row resolves (relaunch on current, or retire) within 2 ticks of the adopt or alerts.
- Owner: WAVE-FLOW-R2; a lane for the 4 unowned QC rows is still missing.

## Do now (ranked)
1. S81-TYPES-R3 / FIX-S81-VPW: stop and relaunch the 8 running col attempts whose spec.json carries OT_S81_VPW_BANK.
2. WAVE-PILOT-FIX: probe budget per class, failed probe shuts the class; env key removal supersedes specs (A).
3. WAVE-FLOW-R2: consume the tree-switch marker once; drop gen_host/gen_hosts from markers; check s81 tools_sha on the
   first tick after the s81 refresh applies (B). Refresh path filter + parallel/quorum replicate (C).
4. FLEET-OPS-R: epyc2 root cleanup; AUTO-RESIGN KeyError 'tag'; hub cleanup timer (E, G).
5. WAVE-PILOT-FIX: INFRA keying of die_plan tool exceptions; heal-verify and backoff; NEEDS-LANE from audit counters,
   name the 4 PILOT-DEADLOCK items (D, F, G).
6. COORD: lanes for the s81 svc closure error (13 fails) and the 4 unowned QC kit_rtl rows.
