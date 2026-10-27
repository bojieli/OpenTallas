# HEAD-R20 plan delta: 26 declared clock slots + spine-trunk M9 riser (HEAD-CORE-R20)

Branch claude/head-r20-plan-1027 = claude/head-r19-plan-1027@df038a2a04 + this delta. Applies COORD 2026-10-27 11:15
HEAD-CORE-R19 ruling (3): the approved 26-slot island delta goes into the HEAD R19 plan batch together with the spine-trunk
8.64-um M9 riser, G0/G0C must stay 0.

## Delta (tools/s81_head/head_r19_island_riser_delta.py, fail-closed; report delta_report.json)
- (a) 26 declared 8.64 x 8.64 slots from the R19 tree (claude/head-r19-tree-1027@6acfb0b663 results/s81_head_r19/tree/slot_delta.json,
  copied here as slot_delta_r19.json, sha256 4ec17c8e...): hd_tile 2, hd_spn 12, hd_spn_end 12, appended to
  partition_types.<t>.clock.die_islands_um (per type = identical on every instance). Each slot is checked against THIS plan's
  hard-core outlines (A 319.68 / B 285.12, i.e. after the R19 outline growth): 0 overlaps, all inside the type outline,
  none already declared.
- (b) clock.spine.trunk = {layer M9, node_x_um 8760.96, lane_x_um 8769.6, riser_um 8.64}: the y-trunk nodes sit at die x 8760.96 =
  a VDD M9 stripe centre, so the vertical trunk legs run on the free lane 8769.6 (VSS-side half-gap). Lane clearance to the
  nearest M9 PG stripe: 5.24 um on the plan's 6.48 grid, 2.00 um on the HEAD-5 12.96 grid (both >= 0.5 gate). Schema: new
  optional clock.spine.trunk object (tools/die_plan/schema.py + regenerated die_plan.schema.json).
- Undo check: removing the delta gives back the input plan dict-equal (only die_islands_um of 3 types + spine.trunk differ).
- Plan sha256 5a61dd5eb9a7... -> 20a6805a32ba98ac8c71aac1b7ce1a20c2e11337729d2860d45c85445331df90.

## Gates (CHECKED, reports in this dir)
- schema validate PASS 0 errors.
- G0 PASS 0 errors / 6 warnings (g0/g0_report.json); G0C (--completeness) PASS 0 errors / 6 warnings, 16/16 types clean (g0c/).
- Tests: tools/s81_head/tests/test_head_r20_island_riser.py (4: plan carries delta, re-apply fails closed, lane-on-stripe
  fails, overlap) + test_head_r19_pins.py + tools/die_plan/test_schema.py + test_mesh_profile_schema.py: 27 PASS (python:3.12 docker).

## Riser cost (own model, UNCHECKED: stage-table fit, straight legs + 2 x 8.64 jog per vertical trunk edge)
Every root->driver path has exactly 5 vertical trunk edges (SRC-Y-YU/YD-..-row root), so the riser adds the same 86.4 um to
all 264 driver paths: insertion TT 3105.0 -> 3119.0 (+14.0), FF 2494.5 -> 2506.3 (+11.8); driver skew stays 0; pair-skew
derate +0.3 ps.

## Independent checks (checks/; own code, no import of head_mesh_r3 / qc_clk_mesh3 / master_plan)
- NUMBER-CHECK R19 tree 6acfb0b663 (nc_tree_numbers.py/.out): legs recomputed from node xy (0 mismatches vs stored), own
  fit of the 16w m2 stage-table rows: insertion TT 3104.96 / FF 2494.45 on all 264 drivers, 37 stages, path 13996.8 um,
  840 repeaters, 526137 um = CONFIRMED (3105.0 / 2494.5). Pair-skew model from the QC b3 raw constants + mesh pitch
  172.8/103.55: TT 31.74+46.83 = 78.57, FF 32.45+41.74 = 74.19 = CONFIRMED (78.6 / 74.2). Sensitivities: a piecewise-linear
  table instead of the quadratic gives 3173 / 2563 (+68 ps; the model form below 450 um is the UNCHECKED part); the derate
  on the tree's own insertion instead of the QC K_TREE gives 72.1 / 67.2; the real M8 mean strap gap is 124.4 um (meta
  103.55), +2.4 ps nominal. All are plan-model numbers (diagnostic; the freeze gate is the real-clock die STA).
- GEOM-27 / HEAD-5 cond. 1 (geom27.py/.out): on the HEAD-5 PG plan 33029005 (M9 12.96@34.56), the R17 tree (e20c843292 and
  1d8b05e75a) and the R18 tree have 32 of 95 M9 clock straps overlapping a PG stripe (short, worst -2.08 um); R19 has 0
  shorts, min gap 1.16 um. The 32 straps R19 moved (+-3.24 um) are exactly the 32 shorted straps (set equality).
  head_mesh_r3 --pg-lanes re-run on 33029005 itself gives straps.json byte-identical to R19, lane_band PASS (0 off band).
- HEAD-5 cond. 2 M9 demand re-probe (m9probe_grt_final.txt, m9win.py/.out): g2.py die probe on this plan with M9 12.96
  (docker, read-only). GRT overflow 0; M9 resource 100.3 M (6.48 grid: 355.7 M), demand 72,676 = 0.07%; M8 0.01%.
  The HEAD plan has no die-level signal lanes on M8/M9 (all 327 lanes are partition lanes <= M7), so the die-top M9 users
  are the probe clock spine + reset nets and the 95 clock-mesh straps. Per 450-um window (write_guides): worst M9 length
  share 0.43% of free tracks, worst cut 2 nets + 3 clock straps = 0.7% of free (gate 60%): PASS.
