# FABLE-FLOW-2200: flow and procedural review, 19:43-21:45 PST 11-17 (FLOW-REVIEW-2200, Opus for Fable)

Read-only. Sources: autopilot/log.txt (1,774 lines in the window), failure_breakdown.py (21:44), ot-run --status,
lanes/FLOW-HEALTH.tsv, autopilot/kit_wave.json, autopilot/kit_wave_stages.tsv, rt/current on 7 hosts, FABLE-FLOW-1900.
Window totals: LAUNCH 326 (s81 286, s81_head 28, QC 12, **KV 0**, HBM 0 parked), FAIL 52, LAUNCH-HELD 34,
LAUNCH-REFUSED 2, REPEAT-STOP 9. Fleet capacity in the window was about 1,000 thread-h; the waste shares below are
estimates against that figure.

## Checked items from the 19:00 list
- rt/current = origin/main 9665f829521c on epyc2/7/8/9/10, intel1, localhost (switched 21:46-21:47). No rt skew.
- r656 PLAN-CONFIG-DRIFT fires (20:48, 21:31). Nobody acts on it (see F).
- s81_head is fixed: OT_SIGNED_VIEW_SHA is now in-tree (tree _d1_t58211f4, commits 85d7b9a 21:25 and c374471 21:42).
- Disk-estimate replicas (WAVE-FLOW-R2) and the r669 archive timeout were not re-checked.

## A. KV silently OFF after the KV-HG6 adopt: 2 h 15 min, 0 launches (new, severe)
- `atomic apply qwen_kvsys KV-HG6` ran at 19:30. SWITCH-SUPERSEDE cancelled 21 KV-HG5 jobs at 19:40.
- The last KV launch was 19:20 (on HG5). kit_wave_stages.tsv has **0 rows on KV-HG6**. All 76 KV rows are HG5 or
  older and have plan_current blank. They are exactly the "superseded-event rows (not counted, retire or relaunch) 76"
  in UNDER-USE.
- At 21:08 a TOOLS-REFRESH tree switch (ADOPT-ROWS) superseded the tree again. Still nothing launched.
- No HELD, REFUSED or KEEP line names a KV item, and `hold_items` = {}. FABLE-PD-KV-2200 says the 16 kv3_pv items
  are held for D22, but that hold covers 16 items, not 60.
- Root cause (process): an adopt only stops old work. Nothing checks that the die then produces current-event rows,
  and RETIRE-SUPERSEDED reports "retired 0 / relaunch-on-current 1" without naming the die. The cause inside the wave
  (allowlist, plan sha or event key) is UNVERIFIED.
- Structural fix: add a post-adopt liveness invariant. Within 2 ticks of any adopt or tree switch, every enabled die
  must have, for each only_item, a current-event LAUNCH, HELD or REFUSED with a reason. Otherwise raise
  `ALERT DIE-OFF <die> <n items>` with a per-item reason histogram. Superseded-event rows must resolve, by relaunch
  or retire, within N ticks, or alert.
- Owner: WAVE-FLOW-R2. KV-HG-OPUS should check now whether HG6 is meant to wait for D22.
- Waste: about 5-8%. KV's share of the idle threads (UNDER-USE 32-43% idle).

## B. A die-wide opt-in env applied to the wrong types: OT_S81_VPW_BANK=1 (new, 20 fails)
- `dies.s81.die_gen_env.OT_S81_VPW_BANK="1"` was added by the 19:01 atomic apply (e013593). gen_phys.py:6701 then
  installs s81_vpw_bank.tcl into every s81 kit.
- The tcl needs exactly the two `vp.u_b0/1` macros of one leaf. col_h9/col_h10 types have none, so they fail at GPL
  with "needs exactly two real VP SRAM macros, got 0": 18 FAIL rows (21:16 x3, 21:31 x15). They were launched at
  20:50 with 12 or 60 replicas each, so each fail cost about 40 min.
- The CLASS-BREAKER opened at 21:31 after 18 fails. Self-stop works, but late.
- "distance exceeds 100um" (x6) and PLACE-HPWL (x6) are design failures, out of scope here.
- Root cause: a type-scoped opt-in is carried in a die-scoped env, and neither the tool nor apply checks that it
  applies.
- Structural fix: (1) `s81_vpw_bank.install()` decides applicability at gen. If the netlist has no `vp.u_b[01]`, it
  writes no tcl and logs `VPW-BANK n/a`. (2) apply refuses opt-in `OT_*` keys in die_gen_env unless the tool declares
  them die-wide; otherwise they go in `item_env` by pattern. (3) The breaker opens after 3 fails of the same class in
  one die, not 18.
- Owner: WAVE-PILOT-FIX. The S81 owner should move the key to item_env `ot_s81sl_leaf__*` now.
- Waste: about 6-9%.

## C. KIT_NOT_SELF_CONTAINED: HEAD fixed, KV still exposed (15 fails, 20:42-20:48)
- s81_head failed 15x on `kit-ops-6/signed_view_sha_head.json`. The breaker opened 20:48 and RELEASED 20:50 on
  "preflight passes again", 35 min before the real fix (21:25). Verified fixed now.
- `dies.qwen_kvsys.die_gen_env.OT_SIGNED_VIEW_SHA` still points to `/srv/opentallas-scratch2/claude/kit-ops-6/signed_view_sha_kv.json`,
  which is out-of-tree. That is the same latent fail, and it will fire the first time KV launches again (A).
- Root cause: path-valued env is not required to sit under `src`.
- Fix: apply and the gen preflight refuse any path-valued die_gen_env or gen_args entry outside the die's src tree,
  for all 5 dies. The breaker releases on a changed input of its fail key, not on a preflight rerun.
- Owner: WAVE-FLOW-R2. Waste: under 1%, because the fails were at gen.

## D. Tool lag and refresh churn (flat to worse)
- TOOLS-LAG: hbm 2,047 commits, QC 950, KV 950, s81 138 (missing r600-r667, including r638, which the serdes holds
  need), head 28.
- KV TOOLS-REFRESH started 5x for the same r407..r459 list (20:15, 20:27, 20:34, 20:42, 21:02) before it landed at
  21:08. Single-flight (1900 B) is still not in place. s81: no refresh in the window. TOOL-SKEW WARN-and-launch x70.
- Root cause: tools are pinned in the die tree, so every main fix needs a new tree and adopt, and each adopt then
  causes A or E.
- Fix: the end state from 1300. Kits take tools/ from rt/current (verified uniform) and the tree pins rtl+plan only.
  Until then, refresh is single-flight per die with flock, and an s81 refresh for r638 is due now.
- Owner: WAVE-FLOW-R2. Waste: under 1% directly, but D drives A and E.

## E. Retries on unfixed causes, and duplicates
- QC ITEM-SYNC `bind_L2BQ_rawall intel1->epyc2 rc=2` every ~2 min (21:36, 21:38, 21:40, 21:42). epyc2 is not a QC
  gen host and its root fs is 100% (2 GB free).
- s81/slice_station__t51 KIT_INPUT_MISSING ran 3x before REPEAT-STOP.
- ORPHAN "would stop" on epyc8 for 1.7 h: 2 older attempts (s81 kv_leaf__t1 a4, leaf__t53__cl958451dd a6) still run
  beside their newer attempts. ORPHAN is report-only.
- QC REPEAT-STOP OOM x6 resubmitted at x1.5 memory: correct.
- Root cause: per-item retry loops have no backoff keyed by (cause, rc), and the ORPHAN stop is not enforced.
- Fix: ITEM-SYNC backs off by (src, dst, rc) and never targets a host outside gen_hosts. ORPHAN enforces after one
  tick when the newer attempt is RUNNING.
- Owner: WAVE-PILOT-FIX (ITEM-SYNC), FLEET-OPS-R (ORPHAN). Waste: about 2-3%, mostly the duplicates.

## F. Holds and config drift (over-hold, rising)
- HOLD-AUDIT TERM-UNREACHABLE went from 0 to 74 at 21:10, right after the s81 d7w ADOPT-ROWS. HOLD-SUPERSEDED is
  72-74.
- PLAN-CONFIG-DRIFT: QC phy_serdes, phy_serdes_b and phy_ucie_kv are outside only_items ("never launch"); 2 QC
  only_items match no item; s81 holds `bk_sel__t2__*` and `dsdv_slice_c1x_C__t*__*` match no item. Twice in the
  window, no action.
- Root cause: alerts have no owner, and holds are not re-keyed at adopt.
- Fix: a drift or TERM-UNREACHABLE alert writes a NEEDS-LANE row per die, owned automatically by the die owner.
  Adopt re-keys each hold to the new event or drops it with a reason, and never leaves an unreachable term.
- Owner: WAVE-PILOT-FIX. Waste: unmeasured (items that never launch), under 1% of fleet.

## G. Hub, state and tick latency
- ALERT HUB-SYNC-FAILED x7: lanes/NOPROG.tsv is a tracked cron table again (1900 E, unfixed), and there was a
  COORD-REVIEW-QUEUE.md commit failure at 21:32.
- **New:** `AUTO-RESIGN PRESTAGE skipped: KeyError: 'tag'` x6 since 20:49. Re-sign prestage is off.
- noprog_stage.py DIFFERS on 7 hosts (unchanged).
- TICK total 737-1312 s (kit_wave_step 590-680 s, reap_stale_attempts 245 s), so launch and reap react 12-20 min late.
- s81 TREE-SWITCH was logged 7x for the same d6z tree. derive_gen_hosts rewrote gen_hosts 3x in 25 min.
- Fix: untrack the generated tables or have their writer commit them. Guard the auto-resign `tag` lookup and alert
  on a skip. Cap kit_wave_step at 300 s and defer the reap. Make TREE-SWITCH a no-op when it is already switched.
- Owner: FLEET-OPS-R (hub tables, auto-resign, tick), WAVE-FLOW-R2 (switch, gen_hosts). Waste: about 2% from tick
  latency.

## H. Capacity and admission
- UNDER-USE 32-43% idle (187 of 432 threads at 21:27).
- intel1: load 118/112, 16 waiters (197 GB), 270 threads committed. At the same time epyc2 is at 25/128 (root 100%,
  scratch2-only), epyc7 at 37/96 and localhost at 5/112.
- GEN-DISK-LOW on the root lanes of epyc10, intel1 and epyc8 (<60 GB).
- Root cause: waiters bind to a host at submit and never migrate. epyc2's root fs is full.
- Fix: a waiter older than one tick re-places to any admitting host (place_spill already exists, so make it apply to
  waiters). Run the epyc2 root cleanup pass now.
- Owner: FLEET-OPS-R. Waste: about 5% (intel1 waiters versus idle hosts). A is the larger share of the idle.

## I. Stale and unowned (slightly down)
- STALE current-event 114 (1900: 121): S81 4 (FAIL-S81-1), QC 11, KV 1, HBM 104 (parked).
- QC still has **4 unowned**: 3 `kit_rtl FLOW @06:21` (15.4 h) and 1 superseded geom. Same as 1900.
- S81 has 48 rows "kit input missing" since 11-16 16:35 on `count-archive-2/s81views_v20261110/...` (deleted view
  pack). They have been stuck 29 h without being counted STALE.
- Fix: STALE also counts rows with a terminal missing_input older than 6 h, even if the row was touched. A view pack
  named by any live row is protected from cleanup.
- Owner: new lane (QC-UNOWNED-KITRTL); WAVE-FLOW-R2 (STALE rule).

## Do now (ranked)
1. WAVE-FLOW-R2 + KV-HG-OPUS: find out why KV-HG6 has 0 rows (A); add the DIE-OFF invariant.
2. S81 owner: move OT_S81_VPW_BANK to item_env leaf types. WAVE-PILOT-FIX: make the tool decide applicability, and
   set the breaker at 3 (B).
3. WAVE-FLOW-R2: move the KV signed_view_sha into the tree before KV relaunches, and add the path-under-src check
   (C). Refresh s81 tools for r638 (D).
4. FLEET-OPS-R: auto-resign KeyError, untrack NOPROG.tsv, enforce ORPHAN, migrate waiters, clean the epyc2 root (G, E, H).
5. WAVE-PILOT-FIX: give owners to the drift and TERM-UNREACHABLE alerts; ITEM-SYNC backoff (F, E).
