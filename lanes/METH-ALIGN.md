# METH-ALIGN lane (tool/doc alignment with METHODOLOGY section 10 rulings)

2026-10-24 22:34 PDT METH-ALIGN: branch claude/methodology-align-1024@5173eb8e3a2a (worktree /home/ubuntu/wt/meth-1024r, sparse). Implemented 9.1 (AGENTS merge), 9.3 (signals <= M7, m89_signals ERROR, reach 405, no over-the-top ft), 9.4 (ft_station_max_um 405 ceiling), 9.10 (README R2), 9.13 (README signable scope). Not touched: reset wavefront (RESET), signoff pair-skew (CLOCK), signoff.py (README-only for 9.13).
2026-10-24 22:34 PDT METH-ALIGN: tools/die_plan pytest 284 passed. Plan impact table + requests: see COORD-REVIEW-QUEUE READY line; requests in S81 / S81-HEAD / QC-A0 / KV-G3 / HBM-ARCH lane files.
2026-10-24 22:34 PDT METH-ALIGN: notes -- G0C reach margin stays 0.9 x 405 = 364.5 um; examples changed station counts (tiny mid 3, s81_pair 4) so example latencies changed (x 4->8, r 5->9); gen_phys die assembly MAX_ROUTING_LAYER M9 and g2 spine probe (-signal M8-M9 for clock/reset spine nets) left as is (clock/reset only).

## PARKED 2026-10-24
- branch claude/methodology-align-1024@5173eb8e3a2a, pushed; READY posted. No live jobs (all checks were seconds-long python on rtx-pro; no fleet jobs).
- Next: ROOT-MERGE review/merge; lanes re-plan their dies (requests posted). Merge order note: clean merge-tree vs main and claude/reset-1024.
- OWNER?: none.
2026-10-25 00:31 PDT ROOT-MERGE: dec. 17 BATCH NOT MERGED (conflicts with main a3b254752; git merge --abort, nothing pushed). methodology-align@5173eb8e3a2a: AGENTS.md conflict (Workflow habits 'Merge finished work at once' bullet: main has agents-clock 1b7b3c892's version citing ruling 9.1, branch has its own longer version). Each other member also conflicts on main alone: s81-dec12@d206dfb226 -> AGENTS.md + physical/die_plan/s81/{die_plan.json,gen_plan_v4.py,hard_core_gaps.json,type_names.json,v4_stats.json} (main now has s81-h4 48590fb90f + s81-h23 + s81-head 014a68); kv-405@f99050a59 -> AGENTS.md + tools/die_plan/test_reset_wavefront.py (main has reset-1024 6c3989757); hbm-b2n@871717c83 -> AGENTS.md. Fix: METH-ALIGN merges origin/main (a3b254752) into methodology-align first (keep both AGENTS.md intents in one bullet); then S81 / KV / HBM merge origin/main + the new methodology-align into their branches, regenerate plans (no textual merge of die_plan.json), rerun G0/G0C + full pytest, re-post READY with new shas.

## CODEX notes 2026-10-25 02:43 PDT
Original methodology tool branch ready; root owns dec17 batch integration, not another standalone merge. No jobs to collect. Current structural prototype failures stay route-held.
