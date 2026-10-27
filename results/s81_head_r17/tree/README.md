# HEAD R17 task 4 - ruling 3 tree fix (symmetric re-site + M8 <=144 um + 12.8 d1 sizing)

Generated Tue Oct 27 07:07:14 AM PDT 2026. Plan physical/die_plan/s81_head/die_plan.json (unchanged). Branch claude/head-r17-tree-1027.

Command (adds `--symmetric --m8-max-pitch 144` to the R15 command):
python3 tools/s81_head/head_mesh_r3.py physical/die_plan/s81_head/die_plan.json --stage results/qc_clk_mesh3/stage_table.json --pg-lanes --spine-columns --pins-a 162.00,163.44,319.68 --pins-b 144.72,146.16,285.12 --symmetric --m8-max-pitch 144 --out <dir>
python3 tools/die_plan/master_plan.py <plan> --out <mp> --mesh <dir> --declared-slots

| item | R15 baseline (rerun) | R17 s1 |
|---|---|---|
| unequal sibling families (tree_balance) | 175 FAIL | 0 PASS |
| drivers / stages | 300 | 300 / 45 uniform, 1140 reps, 685 mm wire |
| sum of per-level max legs | 23887 um | 17488 um |
| M8 mean pitch (export) | 259.2 hard-coded | 103.55 (max gap 114.44) |
| die_pair_skew_model TT / FF | 130.0 / 122.5 (CHECKED, own recompute) | 90.3 / 84.6 (UNCHECKED model) |
| pair_with_core TT | - | 184.7 (core residual ~94, UNCHECKED) |
| clock_sites / island_lattice | PASS / PASS | FAIL / FAIL (109 nodes + 36 drivers off declared islands, max displacement 614.5 um) |

Pair split TT: nominal 31.7 (K_PITCH x mean pitch) + derate 58.5 (OCV x sum of level-max legs). The equal-leg binary lattice lengthens
the unshared path (14.0 -> 17.5 mm), so the derate rises from 46.9; the denser M8 cuts nominal from 50.1. 80 ps is not reached;
an M9 densify to ~88.6 um is estimated to give ~80.6 TT / 74.8 FF (UNCHECKED, outside ruling 3).

Station rows were re-sited onto the y lattice (1875.94 and 15352.22); the half-lattice x nodes land at column +-354.24 (tile boundaries).
These sites are not declared islands/clock slots, hence the new clock_sites / island_lattice FAILs: they need a declared-slot plan delta
(identical per hd_tile type, 12.2a1) or a different lattice offset. Render viewed: tree symmetric about the spine x 8760.96, every row
fed by equal L/R legs, mesh 1 component (124 M8 + 95 M9 straps), drivers on strap 300/300.

Core pin files now come from real views (tools/s81_head/head_pins_from_lef.py):
- elemA: results/physical/head_core_r15/elemA_eco_signed/ot_s81hd_elemA_cv.lef (signed off), ft_mstrap_i M5 (162.00, 163.44)
- elemB: results/s81_head_r17/ot_s81hd_elemB_cv.hold2_r12b.lef (epyc2 head-core-r10/elemB_hold2 routed, NOT signed off), ft_mstrap_i M5 (144.72, 146.16)
clock_entry still FAILs, now as "missing native core clock-pin metadata": plan hd_tile taps are named inst.clk, the real clock pin is ft_mstrap_i.
Needs a plan tap rename (ASK).

Not run: RCX/MC and related-pair STA (die_sta_related.py) on the new tree - next step after the declared-slot delta.

## GEOM-24 PASS-COND (HEAD mesh m5), 2026-10-27 07:25 PDT
- (a) sibling repeaters: `sibling_rep_findings` (head_mesh_r3.py, recorded as tree.sibling_reps) = PASS, 0 findings over
  386 families: equal straight legs + equal nseg per family -> same count at the same k/nseg distances; one 45-stage depth
  on every root->driver path; segments <= 450 um. tests/test_head_mesh_r3_geom24.py (5 pass, incl. fail-closed mutations).
- (b) the R15 'paired M9 lines' were the solid grey partition outlines drawn beside the cyan M9 straps (not doubled
  straps). R17 M9 min column gap 172.8 um (gate mesh.m9_spacing >= 168.48 PASS). Render: outlines olive dashed, M9 x labels.
- (c) head_mesh_export.py emits strap_spans + vias89 + meta.mesh_vias: 11700 VIA89 = 11700 strap crossings by origin/main
  die_clock_mesh.mesh_via_findings (no findings) and by independent recount. Routed-DB OT_MESH_VIAS: no HEAD clock DB yet.
- (d) same tool (head_mesh_r3 tree.arrival_ps, plan model, UNCHECKED): driver skew R15 2.58/6.41 -> R17 0.157/0.130 ps
  TT/FF; insertion R15 3095.9/2492.3 -> R17 3857.9/3103.6 ps (+762/+611, longer symmetric legs, 45 vs 36-37 stages).
- Re-run of the generator reproduced tree_nodes/straps/stubs/drivers byte-identical.
