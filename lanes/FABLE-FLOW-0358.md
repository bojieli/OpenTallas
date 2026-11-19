# FABLE-FLOW: flow and procedural review, 01:43 to 03:55 PST 11-19 (FABLE-FLOW-REVIEW-05xx, read-only)

Sources: autopilot/log.txt (9,648 lines in the window), kit_wave_state.json (03:47), failure_breakdown.py (03:47),
ot-run --status (03:50), kills.log and admit.log on 6 build hosts, rt/history.log, lanes/FLOW-HEALTH.tsv,
lanes/posts of WAVE-PILOT-FIX, FLEET-OPS-R, S81-DIE-R3, WAVE-TICK-1119, and the last review FABLE-FLOW-0200.md.

Window totals (last window in brackets): LAUNCH 69 (140): s81 37, QC 26, head 4, KV 2. FAIL 48 (41).
CANCEL-SUPERSEDED 213 (about 20). Guard kills 85 (51). REPEAT 43 (109). REPEAT-STOP 14 (9). BLOCKED 9.
Of the 48 fails, 22 are S81 leaf / serdes placement (design, FABLE-FIX-S81-LEAF) and 22 are procedural:
KIT_TOPOLOGY_BIND_STALE 6, SRC_MANIFEST DRIFT 4, guard kill / OOM 4, missing or not-copied kit input 2,
stale in-kit cell cap 2, child view missing 2, kit-rtl bind error on leaf t56 2.
Waste shares are estimates against about 900 job-hours in the window; none is measured exactly.

## Ranked by fleet time wasted

### A. S81 and KV trees are adopted before their bind exists: old rows cancelled, new rows cannot launch. Largest, rising.
- S81: the wave switched d8e -> d8f at 02:28 and d8f -> d8g at 03:28 (same event key 3fa87b84b18).
  At 02:46-02:47 it cancelled 183 rows, 196 S81 rows in the window: 146 in the route queue, 24 gen, 19 place,
  6 preflight. col_h9 132, col_h10 15, leaf 15. Only 14 rows were kept as "past place".
- The cancelled rows carry 1,080 row-hours between start and cancel (S81 989). This includes queue wait:
  23 sampled route jobs had kit logs 51-164 min old, so the compute actually lost is UNVERIFIED and smaller.
- The 10 rows launched on d8f at 02:30 failed KIT_TOPOLOGY_BIND_STALE at 02:45 (6 fails) and opened a class
  breaker. The BIND-STALE preflight then held 150 rows (02:32), 229, 249, 259 (03:34). For d8g, 163 of 163
  and 103 of 103 checked rows are stale. S81 now has 9 rows running and 163 enqueued.
  S81 launches after 02:53: 2. Idle threads went 0 -> 39; load on epyc10 fell 379 -> 66.
- KV: tree switched to hg10/d25c at 02:11. At 02:46 "no row on the current event KV-D25c 2 ticks after the
  switch; bind not PASS in the config". bind_report.json is missing on epyc7/8/9/10 (24 SRC-INCOMPLETE lines),
  so KV has no whole gen host. KV launches in the window: 2. 30 rows still sit on KV-D23H.
- Root cause: adoption (tree switch plus supersede cancel) and bind publication are two separate steps, and
  the first runs without the second. Two S81 switches 60 min apart doubled the effect; d8f rows lived 16 min.
- Did the known fix land? Partly. publish_apply.py adopt-bind is on main (fed3e702b9, in rt 668a30c3473b).
  It has not run end to end. It repoints bind_out after the bind is green; it does not hold the tree switch
  or the cancel. S81-DIE-R3 is still doing D8g2 by hand (bind restarted on fed3e702b9bd tools).
- Structural fix: one adoption gate in the wave. A new tree becomes the die's tree only when its
  bind_preflight has zero stale rows on every gen host. Until then the old tree stays current, nothing is
  cancelled and old rows keep launching. A superseded row is cancelled only in the tick where its replacement
  row launches. The class is then impossible: there is never a current tree that cannot launch.
- Owner: WAVE-PILOT-FIX (gate), S81-DIE-R3 (run adopt-bind on D8g2 / D8h and report), KV die owner (D25c bind).
- Share: 10-20% of the window, mostly S81 capacity that is now draining. Estimate.

### B. Memory guard kills: 85 in 2 h (51, 58 before: rising). Estimate 6-9%.
- Per host: epyc10 38 (12), epyc8 23, epyc7 9, epyc9 8, intel1 7, epyc2 0. Victims: col_h9 27, leaf 19,
  slice_station 6, col_h10 7, cbx_q10 3.
- The wave attributed 4 of the 85 (3 INFRA-KILLED, 1 OOM). The rest came back as FAIL_route and counted
  toward STALLED:route: 6 REPEAT-STOP rows (cbx_q10, tt_ctlm, slice_station t37 and t6, leaf t27) name items
  that are in the kill logs.
- Landed since the last review: PLAN_BYPASS is now env-only (BYPASS-ENV-1119, installed file equals rt
  668a30c3473b on the hosts checked). In the window, before it landed, 137 of about 1,260 admissions were still
  bypassed (11%, was 61%). Route kill = infra, never route-make-fail (fed3e702b9, 03:45). Retries book memory
  on the chosen host (3d373bb957). OT_MAXWIRE_POST_SKIP is in kit_wave.json (2 globs) and in gen_phys.py in rt.
  FLEET-OPS-R reported 47ec45b60c as not on main at 03:55; the code is in rt now, so that report is stale.
- Not landed: admission still under-reserves growth. epyc7 has 83 GB available with 56 jobs, epyc9 150 GB
  with 134 jobs, epyc8 191 GB with 121 jobs; all three admit 0 GB and still killed 40 jobs.
- Structural fix: admission charges each running job its class peak minus its current RSS (already computed
  as "peak"), and the guard writes the victim's container name and kill time into a file the wave reads, so
  every kill is attributed by name. With both, a kill can no longer look like a route failure.
- Owner: FLEET-OPS-R. Check next window: kills should fall now that the bypass is closed.

### C. Unchanged relaunch of a failed row: 43 REPEAT lines (109: falling). Estimate 2%.
- The stage-scoped SKIP-SAME-INPUT (3d373bb957) landed and works: launches dropped and 20 FIX-RELAUNCH lines at
  03:41 were released by a named fix (6e07294d169a), which is the intended path.
- Still leaking: ot_s81sl_leaf__t56 reached attempt 23 on the same kit-rtl bind error (rst_n is not a bit of
  w_u_vp_u_rr_rst_n). It was BLOCKED 3x at 02:11 and relaunched twice more: RETRY-RELEASE "released once"
  fires on every new attempt. cbn_q00__cldbcda913 is at attempt 15 on a missing provenance.json.
  kv3_hub_Wi failed on KIT_INPUT_MISSING for the third window. hd_host_w failed KIT_NOT_SELF_CONTAINED
  (sink_bins_4.json) in two consecutive hours.
- Structural fix: a BLOCKED row is released only by a changed fail key or a Fixes-Items line. RETRY-RELEASE
  must not apply to a row whose fail key is unchanged.
- Owner: WAVE-PILOT-FIX. The items: S81-DIE-R3 (t56), QC die owner (cbn_q00), KV-102 (hub_Wi), HEAD-100.

### D. Kill-resume pinned to a retired tree: 4 SRC_MANIFEST DRIFT fails (0 last window: new). Under 0.5%.
- svc_hi_dsdv_svc_rs__t5, svc_lo_dsdv_svc_rs__t5, dsdv_slice_c1x_C__t1 and dsdv_slice_lepw_mu_C__t1 were
  killed, KILL-PINned to their old inputs, and resumed on d8e / d8t trees whose adopted manifest had moved.
  A class breaker opened on s81|src_manifest. WAVE-PILOT-FIX named the cause at 03:24.
- Structural fix: a pin is honoured only while the pinned tree is still the die's adopted tree. Otherwise the
  row relaunches on the current tree. Fix A removes most cases, since trees would stop moving under live rows.
- Owner: WAVE-PILOT-FIX.

### E. Stale tools inside kits and tool skew. Under 1%, but it hides fixes.
- svc_lo_dsdv_svc_rs_w__t1 (02:27) and svc_lo_dsdv_svc_rs__t7 (03:10) failed on OT_NATIVE_CELL_CAP from an
  in-kit native_cell_cap.tcl that main deleted on 11-18 17:58. t1 got a Fixes-Items relaunch; t7 failed the
  same way 43 min later. A retry reuses the kit's launch-time tools.
- TOOLS-LAG: QC 1,333 commits, hbm 2,430, head 326 (missing r698, r708), s81 122, KV 75 (was 1,277: fixed).
  s81_head skew is UNMEASURED 7 times: pin manifest rt/385f61b5582a.manifest.json is missing on the hub.
- TOOLS-DECOUPLE-2 has no post file under lanes/posts (only TOOLS-DECOUPLE). I found no evidence it is alive.
- Structural fix: the kit records the digest of each tool file it copied. At relaunch the wave compares it with
  the die's current tools and regenerates the kit when a file of the failed stage differs or is deleted.
- Owner: TOOLS-DECOUPLE-2, if it exists; otherwise new.

### F. Wave tick: 922-1,163 s (905-1,167: flat). Under 1% direct; it delays A, C and every fix by 15-20 min.
- kit_wave_step+admit 514-781 s, poll_running 161-494 s. REAP hits its cap of 40 every tick.
- WAVE-TICK-1119 landed f2d48f7f08 (one hub ps per 20 s, parallel per-die probes) and says the target is not
  reached and a follow-up lane is needed: serial coord pushes 99 s, plan_dies / bind_preflight 190 s,
  loop_gaps 75-130 s, 4,445 CANCELLED rows kept in the state.
- Owner: WAVE-TICK-1119; the follow-up is unowned (new).

### G. Stale report state (no fleet time; it misleads owners)
- kit_wave_blocked.tsv is header-only and dated 11-15 21:45, while 9 BLOCKED lines in the window say "listed in
  kit_wave_blocked.tsv". kit_wave_needs_lane.tsv is header-only while the state holds 3 needs_lane rows and 5
  NEEDS-LANE posts were logged. Cause UNVERIFIED.
- ORPHAN-DEAD logged "resubmitted" for 23 jobs that the wave had cancelled 35 min earlier. The next line
  corrects it to CANCELLED (not resubmitted), so nothing ran; the first line is wrong.
- failure_breakdown: STALE 104, all HBM (parked; flat). Its live check still names epyc4.
- PLAN-CONFIG-DRIFT: QC only_items sle_ctl__cl503337ff__v1 and sle_ctl__cl67434795__v1 match no plan item.
- Owner: WAVE-PILOT-FIX (tsv writers, orphan line), QC die owner (only_items), new for failure_breakdown.

### H. Disk (small)
- intel1: one ot-run refusal, /srv/opentallas-scratch 26 GB free under the 50 GB floor. kw45 on intel1 wrote
  279 GB in the window (FLEET-OPS-R quota alert, nothing stopped). epyc2 scratch2 129 GB (95: better).
  epyc10 scratch2 90% used, 761 GB free. 10 deletes deferred on epyc9 (kit still mounted).
- Owner: FLEET-OPS-R.

## Did the fixes from FABLE-FLOW-0200 land?
- A1 PLAN_BYPASS env-only: yes (in rt 668a30c3473b). A2 retries book memory: yes. A3 kill attribution by
  container name: no; 81 of 85 kills were not attributed.
- B stage-scoped skip: yes, REPEAT fell 109 -> 43.
- C unknown plan probe keeps the row, probe written at apply: yes (1539ebdea8, 3d373bb957). SKIP-OLDPLAN 1 (5).
- D tick: partly; flat.
- Main tests: WAVE-PILOT-FIX reports the cap tests green at fed3e702b9. test_core_kit_gens_main_tool and
  test_master_slice were red in its sparse clone and are not confirmed on a full clone. UNVERIFIED here.
- KIT_TOPOLOGY_BIND_STALE automation: code on main, never run live; the class grew from 0 to 259 held rows.
