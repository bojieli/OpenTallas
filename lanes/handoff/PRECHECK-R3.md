# PRECHECK-R3 handoff (Opus 5.5, fresh 11-24 07:50 PST)
Job: report-only PRE checks ADV-UNSET-DEFINE + ADV-TREE-DRIFT (bind-tree RTL lag), land on main, run on c9/C1j/A5t5/W6, post to die integrators.
- Landed main 900aae07e1: TREE-DRIFT rtl closure (plan type modules -> tree/rtl module closure; per-file LAG lines with types), UNSET-DEFINE targets by closure (mutant/tb + unreached = summary only), TREE-SWITCH indexes tools/die_plan + blob DIFFERS. Tests test_adv_unset_define.py / test_adv_tree_drift.py.
- Old 05:36 code (655f4cb33f9..2b5bc1d0270) was by the previous lane; no posts by it.
- Lane clone: epyc2 /srv/opentallas-scratch2/claude/PRECHECK-R3/wt. Runs: intel1 + epyc9 /srv/opentallas-scratch2/claude/PRECHECK-R3/runs (run3b.py + lib2/ = landed code; adv3b.sh PLAN TREE OUT).
- Plans: C1j intel1 QC-ALLFIX/rows_j/compose_0726/with_reset.json (tree QC-ALLFIX/cJ/tree); c9 epyc9 s81-allfix-int/c9/p6w_c9_geom_model_t3_tap_1124.json (tree amd1_tree; c9seal_tree E11 pending); W6 epyc9 head-west/plan_w6/source_plan.json (tree head-west/trees/rt_tools_launch/s81_head_r18w6@c0b6e2d03408); A5t5 copy epyc9 runs/a5t5_plan.json (src E11 kv-allfix/grow/a5t5_seed_codex/plan.json, tree E9 kv-allfix/grow/tree).
- C1j posted 08:3x. c9/W6/A5t5 _b runs queued on epyc9 (load cap).
## 11-24 09:3x state
- Landed: 900aae07e1 (TREE-DRIFT RTL closure, UNSET-DEFINE by closure, TREE-SWITCH tools), 6835043bce (UNSET family = name minus last token), 0e4214903e (tools/fleet/gen_rtl_fresh.py GEN-FRESH), 6283925461 (ADV-TIED-BITS in plan_advisory; TREE-DRIFT RTL index 60 s).
- Posted: C1j 08:32, c9/W6/A5t5 08:54, GEN-FRESH + hd_lep0N handoff to HEAD-EAST-REPLAN, TIED-BITS results.
- GEN-FRESH main: STALE 10, GEN-FAIL 12 (some may be sparse-clone NEEDS-FILES), TSV epyc2 runs/genfresh_main.tsv. lep_nr/split fix HANDED to HEAD-EAST-REPLAN.
- TIED-BITS: c9 must bind with asbuilt_run_allfix2_svctied.json (allfix2 predicts ot_hdc_v41x_kreg). QC/KV native frontend = N/A; HEAD portbind N/A.
- Open: rerun the checks on c9seal_tree (E11) once forked; C1j QC as-built is qc_start_1106/runtime/asbuilt_n46r4_final_preview.json (pass --asbuilt).
