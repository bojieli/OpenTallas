# PG-CORECONN-3 (2026-10-28): core_pg G0 on 5 dies + distributed-core IR composed per die at 150-um bumps

Main 4d4c968ee0. 35 mV budget = VDD drop + VSS bounce co-located, die upper (above M7) + below-M7, no split (12.4a b2).
CHECKED = run output of this lane or a cited CHECKED record; UNCHECKED = estimate or unmeasured power basis.

## 1. G0 core_pg, final code (PG-CORECONN-2 merged RM95/96), default WARN vs --strict-core-pg (g0/g0_core_pg.json)
| die | default | strict | core_pg findings | note |
|---|---|---|---|---|
| S81 | FAIL 12E (base, unchanged) | FAIL 133E | 121 = 115 types w/o core_pg_connect (18,993 insts) + 6 LEFs w/o landable PG (479 insts: bf_col 456 M7-only, capc5r 16, bksel_q 4, eng_rr 3) | was 142 before Codex M5 stub writer 470fcd754e (1,618 stubs fixed) |
| S81-HEAD | PASS 0E | FAIL 1E | hd_tile w/o opt-in (5 cores) | |
| QC | PASS 0E | FAIL 2E | coll_ucie, native59 | 15 core types have no plan LEF (not checkable) |
| KV | FAIL 20E (base) | FAIL 21E | kv3_sys_c | 29 core types without plan LEF |
| HBM | FAIL 4809E (base, stale plan) | FAIL 4809E | 0 | 52 core types without plan LEF: blind |
Default verdicts unchanged vs RM-92 baseline; strict adds only core_pg ERRORs.

## 2. Distributed IR (core power spread over each core's own PG landings; PSM lumped ITermNode not used)
New run: S81 col_h10_r2__t1 (g3k5 kit, 4_cts.odb, 1.77 mm2, 67 macros) with kit pdn.tcl + per-layer macro grids
(M4->M5 ROM 35, M5->M6 cores 26; 4 rom_elem_q + 2 bf_col carry their own PDN to M7 and are excluded), macro power 1.0 W/mm2 x
area (conservative; = HEAD measured tile density), std cells STA at register activity 0.263 (HEAD measured; S81 UNCHECKED).
- core landings: worst co-located 0.47 mV (u_c12_2 ROM / qbank) at 1.0 W/mm2 (HEAD hd_tile: 0.35) CHECKED run.
- std-cell glue: worst 6.39 VDD + 6.76 VSS = 13.15 mV, a cell cluster in the 50-um channel between u_e13/u_e14 (rom_elem_q)
  at y 680-700 (render s81_d10_zoom.png, viewed); 849 of 165,827 cells > 3 mV; p99 2.45 mV. Placement-stage (4_cts) cluster.
New run: HBM routed core ot_hbm_xp_aq_tree13_fmt (hbm-cores-r11 k11m 6_final + spef, own PDN, STRAPS sources): 2.35 + 2.30 =
4.65 mV at its STA power 0.0673 W / 0.0198 mm2 = 3.39 W/mm2 (activity 0.263, UNCHECKED basis) CHECKED run.
In-core coefficient: elemA 4.51 mV at 1.16 W/mm2 (3.9 mV per W/mm2); xp_aq 1.37 mV per W/mm2.

## 3. Composed per die at 150-um bumps / 70-um pads (sum of maxima, conservative)
| die | upper (above M7) | below M7 | total | verdict |
|---|---|---|---|---|
| HEAD | 23.16 G12 (NUMBER-CHECKED) | 5.04 (PG-CORECONN-2 distributed) | 28.20 | PASS |
| S81 | 2.1 G12 at 0.115 W/mm2 region model; 8.0 linear at this tile's ~0.44 W/mm2 (UNCHECKED basis) | 13.15 glue cluster (core path 0.47 + in-core ~3.9 at 1 W/mm2 est) | 21.2 (15.3 at region model) | PASS, power basis UNCHECKED |
| QC | su8 local: measured random-stress 22.4 mW (Codex 4fc469ac5c) -> 34.09 at bg 0.5823 / 26.96 at bg 0.3 | 6.602 su8 in-core (real cells + M6/M7 straps, already distributed) | 40.69 / 33.56 | FAIL at canonical bg (bg A0/flattened unmeasured; production QCLM counters pending) |
| KV | 25.39 edge-fit corner (c39) CHECKED; 26.97 interior | 5.48 measured e1 in-core (real cells, distributed) CHECKED | 30.87 / 32.45 | PASS |
| HBM | 11.3 measured SM (PG-ACT5, CHECKED) | 4.65 real routed HBM core in-core at 3.39 W/mm2 + tile landings 1.6 (0.47 x 3.39 scaled) = 6.3 (replaces 5.13 HEAD-copied estimate) | 17.6 | PASS (non-SM/hub map still 10-24 estimate) |
KV/QC below-M7 were never lumped (real cells in signed cores with tile M6/M7 straps), so the ITermNode artefact did not
affect them. GAP (UNCHECKED, risk): tile GLUE below-M7 (the S81 13.15 mV kind) is solved only on HEAD and S81; KV/QC/HBM
numbers are core slices. A KV-like 27 mV upper + a 13 mV glue cluster would exceed 35 if co-located.

## 4. HBM hub toggle window (tools/pg_activity, opt-in HUB=1)
hbm_tb_dump_patch.py +HUB traces the whole tb in the same case window; hbm_sm_activity_cases.sh HUB=1 adds
--root HUB_<u>=tb_hgi_sm_e2e.<u> for every top-level u_* (VM/arb/record/xload/pub/station) and merges per hub instance
(act_merge.py ACT_TAG). Default unchanged. Synthetic VCD check: hub rates exact (q[0] 0.5, q[1] 1.0).
Main RTL needs -Wno-MODMISSING (ot_hbm_smh_transport_group.sv illegal-shape guard module) -> passed via XDEF.
Live: ot-run unit oth-ubuntu-1837203-1793193526, intel2:/srv/opentallas-scratch2/claude/pg-coreconn-3/hbm_hub (build ~65 min).
