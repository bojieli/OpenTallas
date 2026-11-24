# S81-T2-REFLOOR handoff (Opus 5.5; from 11-23 19:15 PST). FAMILY lane under S81-ALLFIX-INT.
Task: die re-floor giving kv_leaf t2 (s_3N_L0) its slot; price (a)/(b), choose, build row, PRE+G0+scoped strict, ROW-REBASED to INT by 11-24 08:00.
Lane dir epyc10 /srv/opentallas-scratch2/claude/s81-t2-refloor (repo/ = ot-lane-clone of main; tool repo/tools/die_plan/rigid_refloor.py; specs spec_*.json; price/*.json).
Base B1 ae3101241d6b = epyc10 s81-j9-r6/b1_tree/physical/die_plan/s81/plan_j9_b1_exact_1123_ae3101241d6b.json. Tail recipe = s81-allfix-slice/row.sh.
## 19:55 PRICE (posted)
- (a) two-row: not buildable (no free 5.3 mm2, die 856.6/858; E-W partners change). (b) east: 42 parts, 21 types, seal ring/IO/PG blocked.
- CHOSEN (c) C2: stack cols2-4 (C,L1,L3,L4) +699.84; t46/47/48 -> 527.04 tall (top kept); col1 L0+C (s_1N_L0,s_1N_C) -155.52; t2 rect [13452.48,17236.8,18135.36,19163.52] = 4682.88x1926.72. 13 types repinned, 44 ports. Full 4700.16 (spec_C) = +6 types incl lepw C/LP.
## Next
- tool: grid-quantize slides; test; push. apply C2 -> tail (row.sh copy) -> PRE + G0 -> scoped strict on touched types.
