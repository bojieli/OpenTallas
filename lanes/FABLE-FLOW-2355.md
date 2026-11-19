# FABLE-FLOW: flow and procedural review, 21:43-23:50 PST 11-18 (FABLE-FLOW-REVIEW, read-only)

Sources: autopilot/log.txt (9,455 lines in the window), failure_breakdown.py (23:44), ot-run --status on 7 hosts,
/var/tmp/ot-oom-age/kills.log on 6 build hosts, lanes/FLOW-HEALTH.tsv (23:08), lanes/posts changed since 21:45,
rt/current on 7 hosts, one live container inspected on epyc8.

Window totals: LAUNCH 90, FAIL 72 (s81 57, KV 11, QC 4), REPEAT (unchanged relaunch) 59, REPEAT-STOP 13,
SKIP-SAME-INPUT 91, RETRY-IGNORED 15, CANCEL-SUPERSEDED 15, CLASS-BREAKER open 5.
Fleet: about 690 running jobs on 624 threads, UNDER-USE idle 0. Waste shares are estimates against about
1,380 job-hours in the window; none is measured exactly.

## Ranked by fleet time wasted

### A. Hosts sit at the memory kill threshold: 58 guard kills in 2 h (rising). Estimate 2-6%.
- Guard kills (MemAvailable < 5%) in the last 2 h: epyc2 41, intel1 13, epyc9 2, epyc7 1, epyc10 1, epyc8 0.
  All-time totals are 387, so 15% of all kills fell in this window.
- Build hosts admit 0-15 GB each (available memory 5-9% of 1007 GB). ot-run shows `reserve 0, fresh 0`, so a job is
  admitted on current free memory while already-admitted young jobs are still growing. The host then crosses 5%
  and the guard kills the youngest process.
- The wave saw 12 of these as INFRA fails. The costly ones are long single-thread synth runs of svc types:
  svc_lo_dsdv_svc_rs__t5 yosys was killed on epyc7 at 23:24 after about 6 h (22.7 GB RSS). A relaunched long job
  is always the youngest on its host, so it is the first victim again: ot_s81sl_kv_leaf__t2 is at attempt 23
  and svc_hi_dsdv_svc_rs__t1 at attempt 10. KILL-PIN "resumes its checkpoint", but yosys has none.
- The hub (intel2) admits 524 GB and runs 13 jobs at load 46/112. No die lists it in gen_hosts, so wave kits
  cannot use that memory.
- Thread load is 2.2-4x the core count (epyc8 load 391 on 96, 1,557 requested threads). That follows the owner
  rule of RAM-only admission and is not counted as waste here.
- Structural fix (no new limit, rails unchanged):
  1. Admission subtracts the unrealised growth of running jobs, using the measured peak the status line already
     tracks per item (`peak`): admit = available - sum(max(0, measured_peak - current_rss)).
  2. An INFRA-killed item relaunches on the host with the most free memory, the hub included.
  3. The guard's age order uses the item's cumulative lost run time across attempts, so a relaunched 6-h synth
     is not the first victim again.
- Owner: FLEET-OPS-R (ot-run admission, ot-oom-age), WAVE-PILOT-FIX (retry host choice).

### B. `lec_async.sh wait` never returns: 5 containers hold a slot for 2.5-13 h (new). About 0.7% of slots, 5 rows stalled.
- Waiters older than 2 h: epyc7 kv3_sys_c 793 min and slice_station__t44 333 min; epyc8 dsdv_slice_c1x_C__t6
  513 min, slice_station__t8 326 min (route), col_h9_r0_p6__t1__pvb38a9d6c 154 min.
- Verified on c1x_C__t6 only: place finished at 15:17 PST (3_place.odb written). The work dir carries
  `lec_async.abort` and `lec_async.done` from an earlier run, the watcher pid 158527 is dead, and `lec_async.on`
  and `lec_async.ready` exist with no `lec_async.rc`. The loop at lec_async.sh:476 waits while on, ready and no
  rc, and never looks at abort, done or the watcher pid. The other four have the same signature but were not
  inspected.
- HUNG-WATCH reports them as "log frozen 750 min but CPU busy; not cancelled (WF-1)". CPU for c1x_C__t6 grew
  31 s in 81 min, and the no-growth timer resets to 0 on any growth.
- Structural fix: the wait loop ends on any terminal marker (abort, done, rc) or a dead watcher pid, and a new
  phase clears stale markers before writing `ready`. HUNG-WATCH measures growth over the whole window, not since
  the last tick with any growth.
- Owner: WAVE-PILOT-FIX (lec_async.sh), NOPROG-FIX-1115 (watch).

### C. Unchanged relaunch after a deterministic tool error: 59 REPEAT launches. About 0.5%.
- Place stage: 6 S81 leaf types (t14, t28, t33, t41, t47, t62) were relaunched 3-4 min after "NS face bank
  cannot fit" with an unchanged fail key and failed the same way after 71 min each (426 job-min). The class
  breaker opened at 21:54; the relaunches went out at 21:58. SKIP-SAME-INPUT caught them only after the second
  fail. The class itself (25 fails, 19 types) is a design cause owned by FABLE-FIX-S81-LEAF.
- Cheap stages: kv3_hub_Wi (KIT_INPUT_MISSING, 14 files under codex-kv-hr-1029/pd/cores exist on no host),
  qkd_pv_fin_s8_pin (no recipe) and ot_s81sl_leaf__t56 (kit_rtl bind error) each failed 5 times. kv3_hub_Wi was
  relaunched 3 more times after its REPEAT-STOP at 22:50, and its fail key changed three times
  (2a0147.., 95436e.., 9659c6..) with no input fixed. Whether the die_ctx fix (live 23:46) ends this is
  UNVERIFIED; re-check next window.
- Structural fix: SKIP-SAME-INPUT applies from the first fail when the full input hash is equal, at every stage
  (gen, kit_snap, kit_rtl, place), since an identical input cannot give a different result. The fail key hashes
  only the item's own inputs.
- Owner: WAVE-PILOT-FIX. kv3_hub_Wi inputs: KV-102.

### D. KILL-PIN relaunches onto a tree that has since changed: 1 item stuck (new). About 0.3%.
- s81/dsdv_slice_c1x_C__t9 attempt 11 was guard-killed on epyc2 after 4.3 h. KILL-PIN relaunched attempt 12 on
  the pinned tree `src_s81_pin_3c913dbdfb23_d8t_1117_work`, not the live d8e tree. That tree fails
  SRC_MANIFEST DRIFT (hash f1525f0d313e, adopted ad2912c9a085), the row became UNCLASSIFIED and is now held by
  SKIP-SAME-INPUT. FLOW-HEALTH shows 3 src_manifest fails at 18:00 as well.
- Root cause: `_work` trees are edited in place, so a pin by tree name does not pin content.
- Structural fix: KILL-PIN checks the pinned tree's manifest hash against the one recorded at the attempt. On a
  mismatch it relaunches on the live tree as an ordinary attempt.
- Owner: WAVE-PILOT-FIX. S81-DIE-R3 should release t9 now.

### E. Smaller items (each under 0.2%)
- epyc4 is terminated and its address answers with another host key: 74 strict-host-key failures in the window.
  It is still in the ot-run host list and in 8 autopilot state files. Fix: one fleet host file, and a retire
  step that removes the host from it. Owner FLEET-OPS-R.
- KV source-follow bind: 127 identical tracebacks ("cached elaboration source changed: bind/kv45/
  group_r2c_native.sv") and 22 missing `kv3/pv_col_pads_*b.json`, all in the first third of the window. Whether
  the loop still runs is UNVERIFIED. Owner KV-D23-COMPOSE.
- Fail classifier picks a non-error line: 2 QC cbn_q11 fails are filed as "PLAN geometry / site" on the text
  "GRTM mode edge_outline image ...". Owner WAVE-PILOT-FIX.
- QC cbn_q00__cldbcda913 fails at gen on stub provenance (qc_cland_w515_n_d8_rsf_codex) and is at attempt 12;
  6 fails since 16:00. Owner QC-PLAN-R3.
- INFRA_KILLED attribution: two 23:00-23:10 fails cite guard kills at 18:15 and 18:52 PST on a different host
  than the container was on. Stale match or 4.7 h detection lag: UNVERIFIED. Owner FLEET-OPS-R.
- TOOL-SKEW UNMEASURED s81_head: pin manifest rt/385f61b5582a.manifest.json is gone from the hub while the die
  still pins it. One hub cron (limit_outage.py) still runs from rt/d0ee4a2afb10.
- TOOLS-LAG: QC and KV 1,255 commits (950 on 11-17), head 248 and missing r698 and r708 (28 on 11-17),
  s81 62 with none missing (138), hbm 2,352 (parked). Owner TOOLS-DECOUPLE.

## Stale and unowned
- failure_breakdown STALE: 102, all HBM (parked): KIT-WAVE-1 75, unowned 11. Five HBM types are still
  ROUTE-HELD geom from 11-13 (140 h), although a visual verdict no longer gates route.
- OWNERS-SWEEP 22:52: 4 S81 leaf rows UNOWNED by a name mismatch (s81sl_leaf vs ot_s81sl_leaf).

## Disk and admission
- No disk refusal or ENOSPC in the window.
- epyc2 scratch2 has 96 GB free against a 50 GB floor (AUTO-RETIRE at 21:00 deleted 0).
- epyc10 scratch2 went 881 GB to 566 GB between 21:20 and 23:44 (about 130 GB/h): floor in about 4 h.
- epyc8 scratch2 falls 250-290 GB/h with 1,194 GB free: floor in about 4 h.
- epyc7 auto-clean missed a pass for 90 min at 22:15 and has run since.

## Skew
- rt/current = origin/main 15677f487981 on all 7 hosts at 23:46. No rt skew.
- s81 live tree is d8e (plan df7446e48ba9). d8f and d8g trees exist and are not adopted.

## Items already dispatched tonight
- Bind inside the live tree broken by the publish rename: confirmed by the leftovers on epyc8
  (`..._d8f_1117_work_orphan_bind2`); a separate `..._d8g_1117_bind` copy now exists. No recurrence in the window.
- Full tree copy of about 65 min: no full-tree copy ran in the window. Not checked.
- Fixes waiting for manual retry keys: confirmed (15 RETRY-IGNORED on stale keys). Fixes-Items (15677f4879) is in
  rt since 23:46; no FIX-RELAUNCH line yet.
- Small STA reads behind big jobs on epyc7: ot-run now names the hub as the next host for a 32 GB job. epyc7
  still has 2 waiters for 210 GB. Partly confirmed.
- Cleanup deleting the latest failed attempt's kit: one sample holds (s81 leaf t14 attempt_11 kit present on
  epyc8, RESULT-RECLAIM "protected"). Two "skip absent" rows failed before a kit existed.
- die_ctx per-type hash (61e6a2d14f, 376694dbec) and snapshot-neutral block hash (78f0714a41): all three are
  ancestors of rt 15677f487981, live since 23:46. Their effect is not yet visible in the log.
