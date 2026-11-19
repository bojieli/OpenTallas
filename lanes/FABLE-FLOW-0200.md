# FABLE-FLOW: flow and procedural review, 23:55 PST 11-18 to 01:57 PST 11-19 (FABLE-FLOW-REVIEW-02xx, read-only)

Sources: autopilot/log.txt (3,824 lines in the window), kit_wave_state.json (01:38), failure_breakdown.py (01:47),
ot-run --status from the hub and 5 build hosts, /var/tmp/ot-oom-age/kills.log and /var/tmp/ot-heavy/admit.log on 6
build hosts, rt/history.log, lanes/FLOW-HEALTH.tsv, lanes/posts changed since 23:55, docker ps on 6 build hosts.

Window totals: LAUNCH 140 (s81 110, QC 22, KV 7, head 1), FAIL 41 (FLOW place 22, INFRA 9, missing input 3),
REPEAT 109 lines on 43 items (59 in the last window), REPEAT-STOP 9, SKIP-SAME-INPUT 55, RETRY-IGNORED 18,
SKIP-OLDPLAN 5, guard kills 51. Fleet: 458 containers on 6 build hosts, UNDER-USE idle 0 of 624 threads, load
1.3-4.6x cores. Waste shares are estimates against about 1,380 job-hours; none is measured exactly.

## Ranked by fleet time wasted

### A. Memory: 51 guard kills in 2 h (58 before: flat), all 6 build hosts admit 0 GB. Estimate 4-7%.
- Kills since 23:55: epyc8 24 (0 before), epyc10 12, intel1 7, epyc9 7, epyc7 1, epyc2 0 (41 before). 21 of the 51
  victims are S81 col_h9_r1 / col_h9_r2 proof-variant kits; one is the S81 proof kit in GRT
  (ap-ageom-kw-col-h9-r1--t1--cl49d7a23e--pv8aaf8508-grt, epyc8 01:24, 9 GB RSS).
- Queue depth is shallow: ot-run shows 8-12 waiters asking 500-800 GB in total; the wave shows 2-18 rows queued
  (peak 18 at 01:24). The hosts are full, not queued.
- Cause 1 (new, measured): 514 of 838 admissions since 23:55 (61%, 7,174 GB declared) went through PLAN_BYPASS,
  which admits at once with no headroom, reserve or cap. Only 65 were admitted on measured memory; 263 used the
  class peak. PLAN_BYPASS was approved on 11-14 for die-plan bind, LATCHECK and G0. Its pattern (ot-heavy-reconcile
  line 1368) matches the words bind, chain, g0, run_gate and latcheck anywhere in the command line, and every wave
  kit launch contains `tools/die_plan/bind.py kit-rtl` or a `..._bind...` path. On epyc8, 55 of 62 bypassed
  admissions were wave kit launches. Per host: epyc2 265, epyc8 62, epyc7 56, intel1 51, epyc9 49, epyc10 31.
  The memory share these jobs then use is UNVERIFIED (declared 8-16 GB each).
- Cause 2: demand. About 170 of 458 containers are S81 col_h9 / col_h10 proof variants (col_h9_r2 about 50,
  col_h9_r1 about 45) at 15-22 GB each. Type count is a design matter (FABLE-TYPE-REDUCE-S81-COL).
- Cause 3: RETRY-HOST reads "most free memory" once per tick. At 00:58 it sent 6 retries to intel1 in one tick;
  intel1 has admitted 0 GB since and killed 2 more jobs (01:19, 01:43).
- Cause 4: INFRA-KILLED attribution is wrong (confirmed; UNVERIFIED last window). At 01:33 svc_lo_dsdv_svc_rs__t4
  and __t5 were both attributed to guard pid 3984042 on epyc2. That pid was a QC coll_ft container killed at 23:37.
  Both rows got a free retry and t5 a KILL-PIN.
- Growth-aware admission (03214eaad37) is live: the status line carries the peak term (epyc2 available 128-178 GB,
  peak 368-410, admits 0-5). The hub has 664 GB available and admits 37 GB under the same charge.
- Structural fix (no new limit; restores the r709 rail):
  1. PLAN_BYPASS applies only to a job that sets OT_HEAVY_PRIO=plan; the argv pattern is deleted. Wave kit launches
     then pass the same measured admission as every other job.
  2. RETRY-HOST charges each retry it places in the tick against the host's free memory before choosing the next.
  3. INFRA-KILLED matches a kill only by container name and a kill time inside the attempt's run time.
- Owner: FLEET-OPS-R (1, 3), WAVE-PILOT-FIX (2).

### B. Unchanged relaunch of deterministic place failures: 109 REPEAT lines, 43 items (rising from 59). Estimate 3%.
- 42 S81 leaf launches in the window; 15 leaf fails were again "NS face bank cannot fit" or "PLACE-HPWL". Example:
  ot_s81sl_leaf__t61 was held by SKIP-SAME-INPUT at 23:56 and 00:09, relaunched at 00:22 with "unchanged fail key",
  failed the same way at 01:32 (70 min), and was relaunched again at 01:38.
- SKIP-SAME-INPUT at flow stages (8fe845a4fe) is live: 55 skips. It does not hold. The hash it compares
  (kit_wave.py full_input_hash, line 12016) includes exec_tools_digest, a digest over every file a kit executes.
  rt moved 20 times in the window, and the 00:18 sync carried the lec_async.sh fix, a kit-executed file. Launches
  then came in bursts right after: 34 at 00:22, 29 at 00:37, 18 at 00:58, 23 at 01:19, 20 at 01:37. How many of
  the 20 syncs moved the digest is UNVERIFIED (the probe timed out on the loaded hub).
- So each flow fix on main re-arms every held row on the fleet, whatever stage failed.
- Structural fix: the skip compares only the tools group of the stage that failed (the fail key already stores
  tools_group and tool_files), plus the plan block, source and env. A place failure is released by a change to a
  place-stage file or by a Fixes-Items line naming the item, not by any rt change.
- Owner: WAVE-PILOT-FIX. The class itself stays with FABLE-FIX-S81-LEAF.

### C. QC N4.3 / N43G switch: 5 SKIP-OLDPLAN rows, 4 of them with an unchanged block. Estimate 1%.
- Yes, the scope was wrong for slw_fe_v1__clfe325744__cldb4efe33. Attempt 5 (launched 23:13 on N42, 3 replicas)
  was cancelled at 01:31 after 2.3 h and attempt 6 was launched at 01:38 from gen. Attempts 4, 5 and 6 sit in the
  same block directory (bdc7d4994b8d2), so the plan block did not change. coll_ft__cla4a25d77 and
  slw_hc2__cla3497502__cl16607c7a were cancelled the same way at 01:11 with unchanged blocks; the wave itself logged
  slw_hc2 as "plan block unchanged, keeps running" at 01:53. sle_st_a_v2__pv4242de79 (01:50) looks the same.
  Only sle_st_a_v2__pv30dda31f__pvd2ec7769 had a changed block.
- Root cause: two paths judge an old-event row differently. The supersede pass waits when the new plan's blocks are
  not probed ("cancelling nothing this tick"). The enqueue-for-route path (enqueue_skip_reason, line 12930) treats
  "unknown" as old plan and parks the row; the next tick cancels it. Any row that reached route enqueue between the
  apply and the probe was thrown away.
- That gap was 38 min for N4.3 (applied 01:15, judged 01:53) and 20 min for N43G, because the tick takes 15-20 min.
  93 live QC rows on 4 older events were exposed. The 01:53 pass then judged them correctly: 23 REKEY, 12 cancelled,
  66 kept past place.
- Structural fix: enqueue_skip_reason keeps a row when the plan-current answer is unknown, the same rule the
  supersede pass uses. publish_apply writes the new plan's block probe into the wave state at apply, so the first
  tick after a switch can judge every row.
- Owner: WAVE-PILOT-FIX; publish_apply part WAVE-FLOW-R2.

### D. Autopilot tick grew from 540 s to 905-1,167 s (rising). Under 1% direct; it sets the delay of B, C and every fix.
- kit_wave_step+admit went from 373 s to 577-702 s. The hub runs at load 219 on 112 threads with 1,894 ot-run
  client processes. kit_wave_state.json is 44 MB; its plan cache holds about 60 QC plan probes back to 11-01.
- Structural fix: keep plan probes for the current and previous event per die only; time the largest steps
  (launch_safe, collect, tool_skew_measure_all, plan_dies) against the hub load. Owner: WAVE-FLOW-R2.

### E. Smaller items (each under 0.2%)
- QC lost a gen host: the N4.3 apply dropped epyc7 (its live tree is behind at 4cc70f43; replicate failed).
  Owner QC-PLAN-R3 / FLEET-OPS-R.
- epyc7 auto-clean: no completed pass for 107 min (alerts 01:30, 01:45; 90 min at 22:15). 2,147 GB free.
- epyc2 scratch2: 95 GB free against a 50 GB floor, falling 12 GB/h.
- kv3_hub_Wi failed 2 more times on missing input and was launched again at 01:56. Owner KV-102.
- HUNG-WATCH posted 5 rows with the log frozen 361-372 min and CPU busy (c1x_C t10, t4, t5; kv3_pv_v3;
  svc_lo_dsdv_svc_rs__t2). Whether they progress is UNVERIFIED.
- TOOLS-LAG: QC and KV 1,277 commits (1,255), head 270 (248, missing r698 and r708), s81 84 with none missing.
- failure_breakdown STALE: 104, all HBM (102). Its host list still names epyc4.

## Question 1: rt/current lag
- ot-tools-follow runs every 60 s. The last 39 hub syncs were 4 min apart at the median (8 gaps of 12-22 min,
  one of 74 min); the 6 build hosts follow within 2 min. At 01:46 all 7 hosts were on f5f0d744f8df.
- The a953377 report was a 13-min gap (01:23 to 01:36), not a standing lag. A fix "waiting for rt" is in practice
  waiting for the next autopilot tick (15-20 min, item D).
- rt should not follow main faster. Each sync that touches a kit-executed file already re-arms every held row
  (item B), and each new rt sha makes a new rt_tools_launch tree per source tree (106-200 per host).

## Dispatched since 23:55: status
- lec_async wait loop (63eab338ae): live. Waiters older than 2 h: 0 on 5 hosts, 1 on epyc7.
- SKIP-SAME-INPUT at flow stages: live, but released by any rt tools change (item B).
- KILL-PIN manifest check: no SRC_MANIFEST DRIFT fail in the window. The log line still says "resumes its
  checkpoint" for yosys jobs.
- Retry host excluding the hub (83edc4e233): live, 11 RETRY-HOST lines, none to the hub; it herds (item A).
- Ghost-row reaper (1b90c7c0cb): 93 REAP-DEAD SILENT and 12 REAP-PROBE lines; effect not checked.
- Fixes-Items auto-relaunch (15677f4879): live, 1 FIX-RELAUNCH at 00:18.
- cancel-rows --no-stop (301dfb02c5): live, 6 rows closed 01:01-01:05.
- Small-job placement: ot-run names epyc2 ("would queue") for a 32 GB job while the hub admits 37 GB. Partly.
- Delta publish copy: N43G apply took 583 s against 1,626 s for N4.3.
- Growth-aware admission (03214eaad37): live (item A).
- epyc4 removal: gone from ot-run status; still in failure_breakdown.
- die_ctx type-scoped hash plus guard: live; the 01:53 pass separated "own block unchanged" (23) from "die-level
  contract changed" (66).
- publish_apply post-bind hardlink copy: not on rt yet; not checked.
- Keep-latest-attempt cleanup: RESULT-RECLAIM refused the protected kit of leaf t61 attempt 8 (1 sample).
