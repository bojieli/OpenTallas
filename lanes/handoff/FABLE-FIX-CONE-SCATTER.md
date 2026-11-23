# PRECHECK-R2 handoff (started 11-22 18:0x PST, Opus; COORD brief)
Goal: 7 static ADVISORY checks (CORE-PARAM, GHOST-MACRO, SITE-COLLIDE, PORT-WINDOW-PAIR, DEPTH-VS-RTL, DENSITY, TAP-BUDGET)
in the plan_gate_pre advisory path (WARN ADV-* lines, never FAIL), unit test per check with a known 11-22 positive;
run over current plans; post per die before cuts (KV D29 02:00, QC V4 ~06:00, S81 J9).

## Dirs
- Lane clone intel2 /srv/opentallas-scratch2/claude/PRECHECK-R2/repo ; work dir intel2 /srv/opentallas-scratch2/claude/PRECHECK-R2/work
## Plans
- S81 J8 c67f4f6ba285 epyc10 s81-j6-r5/j8_cut_intake/plan_candidates/j8_svc_j7_fallback_f2_n1_phy_trial.json (tree s81-j6-r5/j8_cut_tree); SVC 53ad14f1fc91 same dir combined_j8_lepe_f2_n1_phy_svc42_trial.json
- QC V3 24f8b509b6fd epyc10 qc-plan-r13/v3p6/v3p7c5rt/plan.json (tree kw45/snap_qwen_compute/qwen_compute_v3p7c5rt)
- KV D28 44c3cbf51e50 epyc8 kv-plan-r6/d29/base_d28.json (tree kv-plan-r6/d28/isolated_seal_takeover/rh12_rebind/selected_candidate); D29 rows d29/rows.json
- HEAD r18n 341dbb140f8f epyc9 fable-fix-head-lep0n-1122/trees/s81_head_r18n_w11/physical/die_plan/s81_head/prep/NF15f/prep/source_plan.json; r18m 3dd49f406010 trees/s81_head_r18m_e2
## Status
- 18:1x: design = tools/die_plan/plan_advisory.py called from plan_gate_pre.check() in try/except, WARN ADV-<CHECK> lines. Subagents researching checks.
- 18:4x: lane clone has tools/die_plan/plan_advisory.py (driver, CHECKS -> adv_<check>.py modules) + plan_gate_pre ADVISORY class patch (uncommitted; tests pass). 6 helper agents write work/<check>/adv_*.py + tests; TAP-LOAD added per COORD 18:1x (planned tap load vs netlist flops x1.3; placed >1500).
- 22:xx LANDED main 0a84fc98a0: plan_advisory.py + 10 adv_*.py (+PORT-PIN, MERGE-RESET-DEPTH per COORD 20:4x) in plan_gate_pre class ADVISORY. Caches on all gen hosts /srv/opentallas-scratch2/claude/precheck-cache/{cells,flops}_cache.json (snapshot 11-22 18:2x; harvesters tools/precheck/adv_harvest_*.py; NOT yet on a refresh timer). Run outputs intel2 PRECHECK-R2/runs/. Per-die ADVISORY posts sent.
- TODO: PATH-SEAT (COORD 22:4x, helper running -> work/path_seat), run on S81 J9 when it exists; cache refresh timer; re-run on composed D29 (cut 02:00) / V4 (~06:00).
- 19:3x LANDED main 312978162669: + PATH-SEAT (COORD 22:4x) + PHANTOM-STATION (COORD 19:2x); 12 checks total; plan_gate_pre passes base plan. Cache refresh main b7f0a36c30 + intel2 cron :17 (log ~/.local/state/adv-cache-refresh.log). All per-die posts sent (KV, QC, S81, HEAD x2 rounds).
- Open: composed KV D29 (02:00) / QC V4 (06:00) / S81 J9 get the advisories automatically in their plan_gate_pre; re-run plan_advisory.py --all by hand on them if a lane asks. Known weak spots: TAP-BUDGET does not reproduce t5 (as-built split; TAP-LOAD does), SEAT-DETOUR does not reproduce leaf t15 (kit buffer order, not plan), PORT-PIN needs a strict bind out (HEAD none).
- 20:5x rebind DONE on epyc8 (rt dabe421818ef): elab 0, strict bind 0, LATCHECK PASS 873/873; out = trees/s81_j7_lcs2/.../native_bind/out.
- C/D LAUNCHED 20:56 (run-item rt 345ac19b04b3, has chain spill): specs private_specs/FABLE-FIX-CONE-SCATTER/s81_dsdv_slice_lepw_mus_LP__t2_1122205526 (C fence util .5 between rad 20) / _1122205610 (D soft, same); --bind-out fork2 out, --rt dabe421818ef, goal route.
  Work: .../private/FABLE-FIX-CONE-SCATTER/dsdv_slice_lepw_mus_LP__t2_1122205446 (C) / _1122205532 (D). Units runitem-dsdv_slice_lepw_mus_LP__t2-9779 (C) + D.
  Waiters intel2 waiter3.sh pids 2200422 (C-fence-btw) / 2200423 (D-soft-btw); logs waiter_<TAG>.log. Check OT_PLACE_REGION_BETWEEN counts at place.
