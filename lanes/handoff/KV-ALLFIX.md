# KV-ALLFIX handoff (Opus 5.5, started 11-23 16:29 PST). FAMILY + INTEGRATOR for die KV. Brief: COORD allfix_brief.txt (+ ITERATION LOOP).
Base K3g 324af451f9be (KV-D29 gate k3h3 on it; never touch kw45/src_kv_d29_work_r6). Rebase onto the result of record if it changes.
Table: lanes/ALLFIX-KV.tsv. Coordinate: FABLE-OPEN-KV (pc probe A on 121b8cb74ac2), KV-D29, TAP-GRID-R6.
## Dirs (epyc8 /srv/opentallas-scratch2/claude/kv-allfix = A)
- A/tree = ot-tree-fork of the K3g work tree (16:32 PST); A/launch_70b6f = rt_launch_tree (rt 70b6f0430ea9 tools + tree data).
- A/compose.sh TAG LIST: K3g -> rows in LIST -> reprice (baseline D28 plan_c) -> tap_offset_cover fill --form all -> census -> PRE (asbuilt_k3f_vport_semantic_trial_r2_1123.json). Out A/<TAG>/compose.out.
- A/a1.list: batch 1 = TAP-GRID pv2b plan dccab51441bf (K3g + pv_v3e + pv_v1n splits) + PCGUTKEEP b79196b9e7f1 + PCPO3 af31ff23f995.
- Helpers (forks of this lane): KV-ALLFIX-HUBC (A/hubc: E2 c95f773d3e97 + H2/H3/H4 + ahub congestion split), KV-ALLFIX-SYSC (A/sysc: SYSC-D2DOUT rebase from draft 9c5254471085, RANKS 46f088d331af, S3 seats).
## Census of K3g (16:4x): already carried = RINGFORM 97083c85fd86, HGFORM + HGTN-GRID (0 off-grid bank sites), KRSPCORE, row B/V3FT/PADRAM, PCSLIT/PCGUT/PCONEXT/PCKEEP/PCST/PCTAPEGRESS, AFFAULT, PCV1BANK2, FT23STREET/FT20BAND, HST2SITE/T1SPLIT, CLASS-FIX-RHI, HROOT BAND/RING/GEOM, sys_c C/D/SYSCTAP, hub_C E. New = PCGUTKEEP, PCPO3, pv taps, SYSC-D2DOUT, HUBC-E2 + H2-H4.
- pv_v1n SCHEMA-UNKNOWN-KEY x3 = PRE ran 16:15 while KV-D29 k3h2 had swapped old tools into W/tools (schema.py lacks pad_ram/leaf_clusters/keep_types); rerun on rt 70b6f in A1.
## Log
- 16:30 TAKING posted. 16:32 fork started. 16:4x helpers spawned.
