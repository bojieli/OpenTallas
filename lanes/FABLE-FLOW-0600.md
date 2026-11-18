# FABLE-FLOW-0600: procedural and flow failure review (Fable, advisory, 11-18 05:45-06:00 PST)

Read-only review of 03:40-05:45 PST. Sources (intel2): autopilot/log.txt, autopilot/kit_wave.json + kit_wave_state.json,
lanes/FLOW-HEALTH.tsv, tools/failure_breakdown.py, `ot-run --status`, df on 7 hosts, lanes/OWNERS-SWEEP.tsv (05:13),
lanes/posts/ (33 files changed in 3 h), lanes/FABLE-WORKFLOW-0400.md, rt/history.log.
No new holds, gates or approvals are proposed (r703/r704). Host rails stay (r709).
"Share" = my estimate of fleet thread-time lost in this window; idle is measured (UNDER-USE), the split per class is estimated.

## Headline
- Fleet use 39-69% (UNDER-USE on all 11 ticks; 195-378 of 624 threads idle). No memory refusal: every host admits 464-756 GB, reserve 0.
- Launches per hour: 136 (03), 51 (04), 12 (05). Kit FAILs: 11, 10, 21. RECORDED: 14, 3, 6.
- The idle time is not capacity. It is rows that the scheduler will not launch (classes A, B) plus kits cancelled by plan applies (class C).
- 17 of the 32 kit FAILs in the window were one tooling miss (class D). 7 more were two flow Tcl errors. 8 were design.

## Context claims checked
| claim | verdict |
|---|---|
| stops_off on main 47db5762d0e, maybe not live | TRUE, NOT LIVE. Code is in rt/current (5d29d5144001). `stops_off` is absent from the hub kit_wave.json, so every stop still runs. |
| kits use rt tools at launch | TRUE for QC (cbn_q11 a3, tools_sha d4d7438d) and HEAD. NOT SHOWN for S81: no S81 launch since 03:52; TOOLS-LAG s81 still prints 213 commits. |
| supersede local at 63e146bf82c | LANDED BUT DOES NOT WORK FOR HEAD: the block sha contains the absolute tree path (class C). |
| breaker_fix on 4 dies | TRUE (hub config, commit 6757769e384). It is a hand-written release string per die; it re-closes on the next class. |
| OT_SIGNED_VIEW_SHA left outside the tree | TRUE: 47 refused rows in state (KV 33, HEAD 14). Fix on main 5d29d5144001 (05:43). KV repoint is an uncommitted hub edit. |
| rt sync shipped only tools/fleet | TRUE: 17 kit FAILs @rt_tools on 4 rt shas (04:51-05:17) + 3 refresh COMPOSE-FAIL. Fixed aed901b33a6 / 74354c18d2f. |
| 112 unowned, 234 S81 FAILED no relaunch | TRUE and larger: state has 398 S81 FAIL rows; breakdown STALE 142 (S81 84, HBM 57, KV 1). |
| count 279 vs 391 | Transient read miss; 391 confirmed. count_hourly.py fix is pushed (7e011d974aab) but the hub copy is a local edit (class E). |
| ot-push-main re-runs full tests | NOT MEASURED here. One data point: WAVE-FLOW-R2 needed attempt 2 with --no-test. |

## Classes, ranked by fleet time lost

### A. Stops still on after r703 (launch starvation) - share about 25-30%
- Count: 183-207 rows "not launching" per tick. In 2 h: 50 SKIP-HELD (S81 col_h10 "PILOT after tree switch", since 04:25, still on),
  32 LAUNCH-HELD (DEDUP terminal 15, FLOW-GUARD 7, BLOCKED-REPEAT 3), 18 LAUNCH-DEFER RETRY-PROBE (KV 15, HEAD 3),
  20 RETRY-INFRA-STOP "UNEXPLAINED", 8 REPEAT-STOP, 8 DEDUP-WAIT rows, 2 cell-cap FAILs on kv3_hub_Wo (406,241 > 400,000) that r701 already waived.
- Trend: LAUNCH-HELD fell (23 at 03:4x-03:5x, 9 since). SKIP-HELD rose 0 to 50. RETRY-PROBE re-armed at 05:34 for KV and HEAD (proven=false) by the D22 and r3 applies.
- Root cause: r703 was done as code plus a config switch, and the switch was never set. Meanwhile four lanes work around single stops by hand
  (breaker_fix strings, auto_rearm delete, unblock lines). `hold_items` is {} on 4 dies, yet the pilot hold is still produced by the tree-switch code.
- Structural fix: make stops_off the code default and delete the key, so "off" needs no config push. Then delete the dead paths
  (pilot-after-switch, retry_probe, repeat_ledger, class breaker, dedup terminal) in one commit; keep only the r705 full-input-hash skip.
  Delete breaker_fix, auto_rearm, pilot_mode, pilot_max, hold_items_* and the 20 hold_* note keys from kit_wave.json.
- Owner: WAVE-PILOT-FIX (code default), COORD sets `stops_off: true` now as the 1-line bridge.

### B. S81 FAIL rows never re-armed - share about 10-15%
- Count: 398 S81 rows FAIL (place 154, kit_rtl 122, kit_snap 59, gen 21, gen_lint 14, geom_run 14, other 14) + 50 ROUTE-HELD + 20 RETRY-INFRA.
  S81 launched 110 kits at 03:4x and nothing after 03:52. STALE.S81 84 rows, oldest 45.7 h. S81 is 42/394 types signed.
- Trend: flat for 2 h; unblocked in config at 05:41 (S81-COL-FLOW deleted auto_rearm=false, left there since 11-15 "until G3b adopts").
- Root cause: a per-die opt-out with a prose release term that nothing evaluates. Fixes that changed the inputs (VPW Tcl 76 rows,
  restored view 51, svc closure 13, dup-bb 15) reached main and no row moved.
- Structural fix: remove the auto_rearm key from the code. A FAIL row relaunches when its r705 input hash differs from the failed attempt; that is the only rule.
  The S81 tools reach rows only through rt, so confirm the first S81 launch carries tools_sha from rt (TOOLS-LAG line should disappear).
- Owner: S81-COL-FLOW-1118 (rows), WAVE-PILOT-FIX (key removal).

### C. Plan apply cancels running kits (tree path inside the block sha) - share about 10%
- Count: 4 applies in 2 h (HEAD r1 04:1x, r2 04:2x, r3 05:41; KV D22 05:31). 38 running kits stopped (HEAD 8+13+7, KV 10); 37 rekeyed and kept.
  HEAD has 26 types, so each in-flight HEAD kit was killed about once an hour. hd_lep0N lost 71 min at 05:41.
- Trend: not falling. The 05:41 cancel came 31 min after the local-supersede fix.
- Root cause (FABLE-FIX-HEAD-LEP0N, measured): the plan block holds `clock.sink_bins_file` as an absolute path under the die tree. Every tree rename
  changes the block sha of every type with a sink-bins file, so "local" supersede sees them all as changed. Versioned tree names are the cause, not the plan.
- Structural fix: (1) hash file content, never a path, in the block sha (strip the src root from every path leaf). (2) Phase 2 of TOOLS-DECOUPLE
  (one live_<die> path) removes the rename itself and makes this class impossible. (3) The remote stop to epyc7 timed out 3 times at 120 s; it sits inside the tick.
- Owner: WAVE-FLOW-R2 (hash), TOOLS-DECOUPLE (live tree).

### D. rt snapshot incomplete on gen hosts - share about 1% directly, more through A
- Count: 17 kit FAILs @rt_tools (HEAD 9, QC 8) on rt shas 74354c18, ad867205, 89e30890 between 04:51 and 05:17; 3 tools_refresh COMPOSE-FAIL at 04:13
  on rt/530eea87 (src_manifest.py). Each kit waited 10 min, then tripped the rt_tools class breaker on 3 dies, which needed a hand release.
- Trend: zero since 05:17 (aed901b33a6: rt_tools stage mirrors tools/ + common_flow to the gen host).
- Root cause: "rt on a host" has two definitions (hub = full tree, hosts = OT_RT_HOST_PATHS subset), and the rt smoke test runs on the hub only.
  Two lanes hit the same gap 40 min apart and each fixed its own caller.
- Structural fix: the smoke test before the rt flip runs one kit's rt_tools stage on one gen host. A flip that cannot launch a kit is then auto-reverted (already built).
  Delete tools_refresh for all dies now (config still says tools_refresh true on 4 dies; the log says RETIRED).
- Owner: TOOLS-DECOUPLE.

### E. Hub checkout dirty: config edited in place, not pushed - share small now, blocks A
- Count: HUB-SYNC-FAILED on every tick since 05:24 (3 alerts). Local edits: autopilot/kit_wave.json (KV env repoint, S81 auto_rearm), tools/count_hourly.py.
- Root cause: three lanes edit the live config file in the hub worktree; the sync refuses to touch non-log edits. A stops_off commit from another clone cannot land on the hub while this lasts.
- Structural fix: kit_wave.json joins the auto-commit set of the tick (same as logs), so an in-place edit is committed and pushed within one tick.
  tools/ files are never edited in ~/coord; they come from rt.
- Owner: WAVE-FLOW-R2. COORD: commit the two files now.

### F. Config path outside the die tree - share about 2%
- Count: 47 rows refused once (KV 33 from 05:21, HEAD 14 at 04:05); 17 LAUNCH-REFUSED lines. HEAD hd_tile sat refused about 20 min; KV rows until the 05:4x hub edit.
- Root cause: die_gen_env holds absolute paths into a named tree; each apply moves the tree and not the path.
- Fix landed 5d29d5144001 (apply rewrites the paths). Simpler end state: env values are paths relative to the die src root; the launcher prepends the root. Then the outside-tree check and gen_env_outside_allow are deleted.
- Owner: WAVE-FLOW-R2.

### G. Tick length - multiplies every class
- Count: tick 463-688 s (was 183-284 s at 03:00). kit_wave_step 368-573 s; plan_dies 65 s; ssh timeouts 120 s each.
- Effect: every fix above waits 8-11 min to act; "fix to first kit" is 15-25 min, not the 6-11 min planned at 04:00.
- Fix: remote stop and collect run detached from the tick (fire and check next tick); plan_dies cached by plan sha.
- Owner: WAVE-FLOW-R2.

### H. Unowned and stale rows
- Count: sweep 05:13: 487 unsigned rows, 112 unowned. Breakdown STALE 142: S81 84 (FIX-S81-COL-STALE 80, unowned 3), HBM 57 (parked), KV 1.
  2 S81 leaf jobs (t34, t53__cl958451dd) logged "kit busy, container False, logs 286 min old" on 11 ticks (56 lines): result never collected.
- Root cause: for S81 this is class B, not ownership: one lane "owns" 80 rows that no rule relaunches. KV: only_items has 31 names that match no plan item and drops kv3_phy, kv3_phy_v1.
- Fix: class B. Delete dies.qwen_kvsys.only_items (S81 already did). "Kit busy" with no container and logs older than 30 min is collected as a result.
- Owner: OWNERS-SWEEP (hourly), KV-TYPES-SWEEP (only_items), WAVE-FLOW-R2 (kit busy).

### I. Disk (rail, r709: keep)
- intel1 scratch2 67 GB free (99%), floor 50, falling up to 62 GB/h; 52 jobs run there. GEN-DISK-LOW twice. Cleanup cannot free it:
  1,095 GB in kw43-wave-1109n is all live or current. Other hosts 198 GB-2.3 TB free; hub 134 GB root, 1.2 TB scratch2.
- Root cause: gen-host choice ignored free space until guardroot landed at 04:2x (gen_host_min_free_gb intel1 150 is now read by derive_gen_hosts).
- Fix: none new. Check at 06:30 that no new kit lands on intel1; if one does, the key is not applied to roam placement.
- Owner: FLEET-OPS-R.

## Do now (ranked)
1. COORD: commit the hub's kit_wave.json and count_hourly.py edits, then set `stops_off: true` (A, E). Largest single gain.
2. WAVE-FLOW-R2: block sha without tree paths (C). Until it lands, HEAD-PLAN-R4 and KV-D23 batch plan changes into one apply.
3. WAVE-PILOT-FIX: stops_off as code default, delete auto_rearm, pilot, retry_probe, breaker and dedup-terminal paths and their config keys (A, B).
4. S81-COL-FLOW-1118: confirm the first S81 relaunch wave after 05:41 and its tools_sha (B, D).
5. TOOLS-DECOUPLE: rt smoke on a gen host; delete tools_refresh; start phase 2 live tree (C, D, F).
6. WAVE-FLOW-R2: kit_wave.json in the tick's auto-commit set; detach remote stops from the tick (E, G).
7. KV-TYPES-SWEEP: delete KV only_items (H).
