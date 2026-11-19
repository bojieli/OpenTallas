# FABLE-FLOW-1750: procedural and flow review (Fable, advisory, 11-18 17:43-17:55 PST)

Read-only review of 15:45-17:47 PST (lanes down 15:40-17:30, fleet unattended). Sources (intel2): autopilot/log.txt (7,783 lines in the window),
kit_wave.json, kit_wave_state.json (saved 17:29), OWNERS.tsv, rt/current = 05ebb48a43a5 (kit_wave.py, ot_delete_guard.py), free / loadavg /
kills.log on 6 hosts, lane posts. No new holds or gates are proposed (r703); host rails stay (r709). "Share" is an estimate against about
1,240 job-hours (about 620 running jobs x 2 h).

## Headline
- S81 is NOT launching on D8e yet. Launches in the window: 61 (S81 37, QC 14, KV 7, HEAD 3). All 37 S81 launches carry plan block
  e291d6a8e740 on the d8t tree; 0 carry df7446e48ba9. The wave adopted the D8e tree at 17:46:56 (ADOPT-ROWS) and SWITCH-SUPERSEDE said
  "current plan blocks not probed yet, cancelling nothing this tick". State at 17:29: S81 135 RUNNING + 218 ENQUEUED on e291d6a8e740.
  The event key did not change (3fa87b84b18), so only the plan block tells d8t from D8e. No launch older than d8t was seen.
- D8e will launch into the memory storm: gen_hosts are epyc8 (80 GB available, load 184 on 96 threads), epyc10 (73 GB, load 192) and
  intel1 (204 GB). The tree is absent on epyc7 (337 GB available) and epyc9 (210 GB). It is present on epyc2, which is not a gen host.
- Unattended 2 h: wave FAILs 48 (INFRA / memory kill 16, KV cell cap 12, QC kit_topology 8, S81 serdes OT_BOOT_RELEASE 5, other 7).
  Autopilot verdicts 65: memory kill 47 (41 before), post-CTS stop 7, flow error 6, orphan 2, routed-not-signed 1, GRT overflow 1. SIGNED 0.
- Idle: 56-75 of 624 threads (9-12%) on intel1 / epyc2 / epyc7 the whole window, while epyc8 / 9 / 10 ran load 150-300 on 96 threads.
- No routed unsigned kit was deleted since 15:55 (class B). The one routed result (s81_head/hd_host_n) was kept by the new rule.
- QC slw_stm: not the repeat ledger and not SKIP-SAME-INPUT. The select loop drops the parent type before it expands (see class I).

## Classes A-G

### A. Memory overcommit: 47 verdicts, rising (41 at 1555), now on three hosts
- Guard kills by hour (PST): epyc10 27 (15h) / 22 (16h) / 0 (17h); epyc8 4 (16h) / 7 (17h); epyc2 25 (15h) / 3 (16h). 9 PREGRT_HOLD_FALLBACK
  rc 137. One kill is reported up to 4 times (pid 2981465 on epyc8 -> 4 svc_lo rows FAIL), so one shared job loses 4 rows.
- Now: epyc10 934 of 1007 GB used, epyc8 927, epyc2 886 (121 available); epyc7 337 and epyc9 210 GB available.
- Root cause unchanged: admission on free memory at admit time (measured-peak reservation still not active), S81 limited to a host set
  that is already full, the guard kills the newest small process. New: resubmits after a kill go back to the same hosts ("free retry on
  another host" in the text, epyc2 / epyc10 in the SUBMIT line, 4 of 6 resubmits at 17:37-17:42).
- Structural fix (self-stopping): as 1555 (reserve the recorded per-type peak; victim by memory freed). Add: publish_apply copies the
  tree to every wave host before it switches the die, so gen_hosts = all hosts by construction; the resubmit excludes the kill host.
- Owner: FLEET-OPS-R; TOOLS-DECOUPLE (replicate at publish); S81-DIE-R3 (D8e tree to epyc7 / epyc9 now). Share: about 4%.

### B. Deleters of routed unsigned results: 0 deleted, fixed in the two open tools
- grt_arm_reclaim now keeps 5_2_route.odb / 6_final.odb unless a newer attempt routed (kit_wave.py 10062); ot_delete_guard.refuse()
  carries the routed predicate (ROUTED_FILES, line 189), so auto_retire inherits it. 39 reclaim lines: 15 guard REFUSE, 8 skip
  signoff.json, 6 rc 0 (all QC su_l1 kit_topology fails, never routed), 5 sweeps. Autopilot DELETED 5, all post-CTS stops (not routed);
  KEEP 1 "routed attempt (6_final.odb)" (hd_host_n).
- Left: the routed keep was exercised once. auto_retire journal lines were not readable from here (unit name), so its side is by code only.
- Owner: FLEET-OPS-R to confirm one REFUSE "routed result not signed" in an auto-clean pass. Share: 0 this window.

### C. Late ECO: runs now, 1 of 1 real run failed in the ECO itself
- hd_host_n: late ECO ran 494 s (was 1.5-10 s "pass dir not staged"), ended "ECO b10 route / clock-freeze check / finish failed", TT
  53.26, FF -129.41, DRC 3. So the staging fault is gone for new kits; the result is now a design / ECO result. slice_station__t24 a21 still
  lists "prd_mk.sh b10 failed (pass dir not staged)" (admitted before the fix; FF -20.37, the nearest S81 sign-off).
- Fix: unchanged (ECO tools from rt/current at ECO time; prd_mk last line in the reason). Owner: TOOLS-DECOUPLE. Share: under 1%.

### D. Known-structural launches: stop placed 2 h late, col_h9 ran unattended
- 0 new col_h9_r1 / r2 launches in the window (3 col_h9_r0_p3). But the rows already live stayed: 17:29 state col_h9_r1 23 RUNNING +
  37 ENQUEUED, col_h9_r2 8 + 50 (same as 1400 and 1555), col_h9_r0 29 + 29. The first STRUCT-STOP line is 17:38 (S81-DIE-R3, one row,
  "a D8e plan block releases it"); state struct_stops was still empty at 17:29.
- GRT-EDGE auto still re-arms rows after a GRT overflow (7 lines: leaf t38 / t50 / t61, station t22 / t44, hd_tile, slw_st_b_v1).
- Root cause: the stop is a lane action, so it did not happen while lanes were down. Fix as 1555: the classifier writes the stop.
  With D8e live, SWITCH-SUPERSEDE must cancel every running row whose D8e block differs, in the same tick as the probe.
- Owner: WAVE-PILOT-FIX; WAVE-FLOW-R2 (supersede on the next tick). Share: about 4.5% (31 jobs x 1.75 h), plus the d8t rows below.

### E. Tick: better, still 10-20 min
- 1145, 625, 1244, 773, 786, 601, 765 s (median 773; 1300-1600 at the worst, 521 at 1400). poll_running fell to 27-440 s; the wave step
  is now the cost (320-740 s: plan_dies 87-119 s, launch_safe 35-76 s, tool_skew 40-52 s, collect 42-179 s). STOP-SURVIVOR on epyc7
  still times out at 120 s (4 lines). Fix unchanged (per-host batched probe with a budget). Owner: WAVE-FLOW-R2. Share: 0% compute.

### F. Orphans: 2 verdicts, 1 stopped at 17.2 h
- infra-orphan 2 (col_h9_r1 "client lost, kit logs idle 3.4 h", then KIT-LOST: run_kit.sh missing on the hub). ORPHAN stopped on epyc8
  after 17.2 h (leaf t61 attempt 4, older than attempt 5). REAP-DEAD 359 lines, still "reported only". Fix unchanged. Owner: WAVE-FLOW-R2.

### G. KV cell cap: 12 FAILs, cap still in force, now self-stopped
- hub_C 709,137; hub_Wo 401,310; pv_v1n 422,434; pv_v2n 404,232; pv_v3n 411,146; pv_v3 432,098: two FAILs each, then BLOCKED-PLAN
  "the same failure 3x" (5 types, owner KV-102). The repeat stop ended the loop; the r576 cap the owner ordered deleted on 11-14 is still
  the reason five types within 8% of it do not build. Fix: delete the check. Owner: KV-102. Share: under 1% compute, 6 types idle.

## New in this window

### I. QC slw_stm (4 rows, no launch since 13:06): the parent row hides its unsigned classes
- Facts: the four items are in only_items and in the N4 plan (blocks 3a7b403e, 410a1411, 4f1e7b22, dedda5fa). They have no SKIP-SAME-INPUT,
  REPEAT, BLOCKED or struct-stop line since 13:00, and no row on event s29q103S4Q9N4. Their rows on the same block key are CANCELLED
  SUPERSEDED from L2 (11-17 19:52 / 23:46), three of them with the reason "relaunched on the current event", which never happened.
  Repeat ledger: state empty, only mem_x 1.5; it does not hold them.
- Cause (code read, not a dry run): select() walks OWNERS.tsv parent rows. slw_stm_v1 and slw_stm_v2 are SIGNED-UNVERSIONED there (a
  sibling class or an older block is signed), and QC take_states is NEEDS-KIT / FIX / KIT-PLACED / PLAN-STRUCTURAL / ROUTING / GEOM-REQ /
  REVIEW. kit_wave.py 2908: a parent whose state is not in take_states is dropped with a bare continue, before class expansion and
  before any skip reason. The only exception (KW-RELAUNCH-1) needs a retry key on a class item. stale_cancel() never gets to run.
- So the 17:42 change by QC-SLW-STM-1118 (place memory 112 GB) will not release them.
- Size: 37 only_items have no live N4 row under a SIGNED-UNVERSIONED parent (sle_hc1, sle_fe_v1 x2, coll_ft x2 ...). Most are
  probably signed on their own block; each needs the per-class check.
- Structural fix: select iterates the plan classes, and a class-split parent takes the state of its least advanced class on the current
  plan. Every only_items entry that does not launch gets its reason in the per-tick skip summary (no silent continue).
  Now: a retry key on each of the four class items uses the existing exception.
- Owner: WAVE-PILOT-FIX (select), QC-SLW-STM-1118 (keys now). Share: 0% compute; 4 types x 4.7 h, third report of this class (1400 H, 1555 H).

### J. Plan event applied while the old plan kept launching
- D8e passed G0 at 15:24 and was applied 17:37. In between the wave launched 37 S81 rows on d8t and resubmitted killed d8t rows until 17:42.
  Rows whose block changed in D8e are lost work; the count is known only after the block probe.
- Fix (no hold): when a publish is running for a die, launch_safe orders rows whose block is equal in the candidate plan first; the
  block diff is already computed by publish. Owner: WAVE-FLOW-R2 + TOOLS-DECOUPLE. Share: up to 6% (37 launches), to be measured.

### K. Smaller
- epyc2 left the host list at 17:15 (scratch2 34 GB free) but still receives resubmits (4 SUBMIT lines 17:37-17:42); disk_wait rows 22-23.
- QC su_l1 x4: kit_istations depths [4, 5], 8 FAILs, now SKIP-SAME-INPUT (24 lines): self-stopped, owner DIE-QC-103.
- S81 serdes t3 / t4 / t12 / t14 / t16: OT_BOOT_RELEASE "expected 3 kept stages, found 0", 5 FAILs, one cause; owner FABLE-FIX-S81-SERDES.
- QC cbn_q11: OT_XSTN_STRETCH 64 / 58 paths, 3 FAILs (siting); cbn_q00 WAIT-DEP 2, BLOCKED-PLAN.
- Log noise: CELL-BIG 2,424 of 3,385 wave lines (72%).

## Do now (ranked)
1. S81-DIE-R3 / FLEET-OPS-R: copy the D8e tree to epyc7 and epyc9 and add them to S81 gen_hosts before volume (class A).
2. WAVE-FLOW-R2: confirm on the next tick that SWITCH-SUPERSEDE cancels changed-block d8t rows and that LAUNCH lines carry df7446e48ba9.
3. QC-SLW-STM-1118: retry keys for the four slw_stm class items; WAVE-PILOT-FIX: select by plan class, reason for every skip (class I).
4. FLEET-OPS-R: measured-peak reservation; resubmit excludes the kill host (class A).
5. WAVE-PILOT-FIX: classifier writes the struct stop (class D). KV-102: delete the cell cap check (class G).
6. WAVE-FLOW-R2: wave-step time (plan_dies, tool_skew) and per-host probe budget (class E); SILENT rows through ORPHAN-DEAD (class F).
