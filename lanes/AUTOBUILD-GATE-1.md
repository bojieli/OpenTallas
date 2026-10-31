# AUTOBUILD-GATE-1 — plan-time AUTO-GEOM in G0C (OWNER 12.23 (A))

Branch claude/autobuild-gate-1-1030@6cd597e5763 (on origin/main d518d908345). Files: tools/die_plan/plan_geom.py (new),
tools/die_plan/check.py (G0C hook, --plan-geom enforce|report|off), tools/die_plan/test_plan_geom.py (7 tests).
Same rules, same limits (constants imported from tools/autopilot/geom_rules.py): clock_reach <=220, grid-tap sink load
<=1500 (plan sinks = lower bound), pin_reg p90 30 / max 150, r2r <=405 between plan stages, aspect <=2.0, partial_face.
Exceptions kept: S81 slice_station partial_face (COORD 22:24 (a)); QC sl[ew]_ aspect (COORD 18:54). No fill/empty/
std_band/GRT/pin_density (placement-only, stay at AUTO-GEOM). Reset-leaf->consumer r2r estimate = WARN only (3 FP).

## Validation [CHECKED, my scripts vs kit-wave geom.tsv/auto_geom.json]
| set | rule | hit | miss | false FAIL |
|---|---|---|---|---|
| S81 e50a stations (25) | clock_reach | 25 | 0 | 0 |
| | tap load | 7 | 0 | 0 |
| | partial_face (EXCEPTION) | 23 | 0 | 0 |
| | r2r | 0 | 2 | 0 |
| | pin_reg p90 / max | 8 / 1 | 14 / 10 | 0 |
| QC qc49 non-slice + stm (14) | clock_reach | 14 | 0 | 0 |
| | tap load | 14 | 0 | 0 |
| | aspect (now EXCEPTION) | 11 | 0 | 0 |
| | r2r | 0 | 14 | 0 |
| | pin_reg | 2 | 12 | 0 |
Misses explained: S81 r2r t14/t26 = reset leaf feeding landed-slot eq regs (gen_rtl reset tap from j/k site, face_flops
places at (j+1)/k, reset_taps.tcl not re-pointing) -> FLOW (AUTOBUILD-PIPE-1). pin_reg misses = ring key order / pinslot
FLOW class (GEOM-84/85); plan gives a lower bound. QC r2r misses = landing-ring internal logic (u_cland_rst_* ->
u_cland_fstart_*, tt_ctlm u_rrl_6 -> u_bout_tl) not plan stage sites. sle_ctl NO_3_PLACE = place failure, not a GEOM rule.

## Plans of record [CHECKED, full run]
S81 plan_h2_2249 (main, etap 1989298f5e5b): 190 FAIL / 1 PASS / 12 not-evaluable (landing band absent -> WARN).
clock_reach 188, tap load 144, partial_face 131 (+39 EXCEPTION), pin_reg 49/27, r2r 23, aspect 12. Stations 45/46 still FAIL
reach 344-688 (expected until the DIE-S81-39 relaytap event; 7d35426daf7 not pushed -> UNCHECKED).
QC plan_qc50: 116 FAIL: reach 115, tap load 115, partial_face 81, pin_reg 61/44, r2r 11, aspect 18 (+81 EXCEPTION).
Non-station plan FAILs have NO measured kit yet (UNCHECKED vs AUTO-GEOM) -> default mode = report.


Tests: test_plan_geom.py 7/7 + test_check.py/test_reset_tree.py pass. Full tools/die_plan suite on epyc2: the 23 failing tests outside
ft_reserve fail the SAME way on origin/main (sparse checkout missing macros/results, yosys-abc); test_partition_ft_reserve
5/5 pass from repo root (it fails from the tools/die_plan cwd on main too: ModuleNotFoundError tools). G0C runtime +~65 s on S81.
- 2026-10-30 23:51 PDT RESULT AUTOBUILD-GATE-1: READY ROOT-MERGE claude/autobuild-gate-1-1030@6cd597e5763 (report mode default); ASK COORD enforce flip; PARKED, worktrees removed.
