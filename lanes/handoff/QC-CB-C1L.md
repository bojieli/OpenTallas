# QC-CB-C1L handoff (combined cb plan C1l; started 11-24 14:59 PST from QC-ALLFIX)
Job: C1l = C1k 7fbc73d3f7cf + (a) PIPESEAT 002c58551eec + (b) CB-TAPBINS (bins 1c9f81e0280c; cb plan from QC-CB-SPREAD-R2 acb retap, intel1 c1k_tree/physical/die_plan/qwen_compute/plan_of_record/c1k_cbtapbins/cb/plan_out.json) + (c) CB-COREPHASE (QC-CB-PROBE, unbuilt) + QC cbc_pass rows. Strict bind -> 1 pilot cbn_q00__cl622f65d2 to GRT -> all 17 cb to route.
Work dir: epyc10 /srv/opentallas-scratch2/claude/QC-CB-C1L (tree = ot-tree-fork of epyc7 QC-ALLFIX/cK/tree, fork.log). Merge tool: merge3.py (3-way JSON delta merge, conflicts exit 2).
Ruling 15:0x: bind + pilot on (a)+(b) as soon as both land (pilot gate = GRT overflow); COREPHASE folds in before the 17-type route launch.
CBC-FALLBACK: CBC-RULES-1119 hourly lists QC 0 types since 11-21 12:17 (last QC rows slw_st_a_v2 x2, gone since); current list is S81 only.
