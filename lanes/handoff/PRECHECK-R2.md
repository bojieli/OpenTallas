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
