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

## 17:18 PST Codex handback

- A1 source fork completed. The initial compose run used a relative a1.list across a working-directory change. It failed to read the file and was stopped at exact own E8 scope 3215648 to prevent an uncomposed false result.
- Corrected A1 is running as intel2 `kv-allfix-a1-compose-r2-1717`, E8 `oth-ubuntu-3235488-1795483029`, output `A/A1r2/compose.out`. Both PV tap grids and both PC rows applied. Reprice adjusted L1316/L1378 by +2. Current candidate `A/A1r2/plan.json @0c9c828a2857`; TAPOFF all 56/56 with zero missing/unevaluated/stale. PRE in flight. Preserve the job. Next intake still includes SYSC-D2DOUT mandatory L343 hop fix and pending hub_C H2–H4 with E2. No CAD route or STA started.
