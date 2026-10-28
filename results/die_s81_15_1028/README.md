# DIE-S81-15 (S81 die owner, 2026-10-28 11:55-14:0x PDT)

Data: intel2:/srv/opentallas-scratch2/claude/die-s81-15 (cp13 = go13 probe, cp14 = go14 post recipe, not yet run).
Tool base of this branch: origin/main 9644a2fed8 + APPROVED claude/die-s81-14-merge@fe3dd4d1a9, die-s81-13-rt@ca2f7d1f3c (RM169),
flow-onemodel-2@3e95a78976, clk-inv-cal-1@8795df0cf, flow-onemodel-3@ad1358b21c (merges, no conflicts).

## 1. Tool: die_trial opt-in --cell-paths (5f0bae9bc0, READY ROOT-MERGE)
Start-tree retime at the EXISTING leg repeaters (COORD 11:54 (4)): tree.json taps carry the physical cell path (the
--tap-pad form, without pads), so trial_tap_arrivals exports every leg repeater as a tree-path node and
count_align_plan --start-retime-up can put a retime stage at any repeater. Netlist/placement byte-identical; default
tree.json byte-identical. tests/test_die_trial_cell_paths.py (3) + test_die_trial*, test_clock_edge_readout, test_count_align* PASS (CHECKED).

## 2. Probe on go13 (om2 both-edge arrivals; same tools both sides; CHECKED own runs, cp13/)
scripts/physpath.py adds the cell paths to an existing tree.json (same code as the opt-in).
* Intra die STA (inv2, table/shared/spice/cppr-lca, --core-insertion declared = PLANNING): byte-equal with and without
  cell paths: TT setup -106.97 / FF hold -724.05 / kit-contract W180 -502.09 (neg 1279). DECLARED mode, not a gate pass.
* CA width, --start-retime-up --start-retime-max 8 (cp13_summary.json):
  | start tree | edges | width-unclean (FAIL) | retime nodes | min sync dist | crossings FAIL | worst lo/hi |
  | geometric (tree nodes) | 1155 | 6 | 498 | -1.0 | 0 | 105.5 / 107.7 |
  | --cell-paths (repeaters) | 988 | 0 | 331 | 140.4 | 0 | 105.5 / 107.7 |
  So item (ii) "segments <= 350 ps" is met at the repeaters, no new tree nodes (no inv2 stage quanta).
  The FLOW-ONEMODEL-2 4 FAILs (s_7N_L2<->s_7S_L4, L_width 4960) are gone under the CLK-INV-CAL-1 rows already
  (geometric run too): depth 8, margins 891.7 / 426.2. Plan runtime ~40 min with cell paths (geometric ~16).

## 3. Early core taps vs signed views (COORD request; early_core_modules.json)
1696 early core taps = 20 core modules; 0/20 have a signed view (the 15 signed S81 cores sit on common-latency taps).
rom_elem_q_qxpq_w10 864 + bf_col 456 = 78 %; + ve_m/vsw/vn_a/vn_b (75 each) = 96 %. Posted to COORD-REVIEW-QUEUE.

## 4. go14 (DIE-S81-14 build, merge-early) NOT collected: kit still in DME at 2 h 07 (go13: 81 min)
py-spy (CHECKED): die_trial.dme_region_tree join() recursion 24+ deep (join(join(a,k),o), two recursive calls per level,
depth cap 24) under merge_point_delay. Cause (inferred, UNCHECKED): merge mode puts the declared early (up to ~580 ps x
1.78) into the sink delay S, so |S_a - S_b| exceeds the merge reach on most core-tap merges and join() descends to the
cap with 2 calls per level (exponential). Fix for the go15 build: in merge mode an S gap larger than the reach is closed by a
snake/delay leg on the fast side (already priced by snake_leg), not by join-down; or memoise join. Post recipe ready:
scripts/cp14_post_go14.sh (render with the go13 legend, legs > 450 um vs go13 3256, cell-path proof, die STA declared +
view (fail closed), lpo, CA width/phase + bind + STA).

## Next (DIE-S81-16)
COORD 13:5x: go15 = ONE build on plan_s11 + --cell-paths + branched slew legs. plan_s11 = plan_s10 + (a) bf_col clk pin
fix 990771bcbb (local branch claude/cores-early-1-s81-1028 in the intel2 repo), (b) _gb ROM master bind (plan_s10 + col_h9/h10),
(c) bf_col/ROM-elem early taps from the CORES-EARLY-2 signed views (~16:30; else CORES-EARLY-1 measured 250-320 TT,
UNCHECKED), (d) delta_signed_view_pins_1028.py (claude/cores-early-1-pins-1028@cb37095db7, rstg/payload536). vq: re-kit on main
RTL via autopilot (view NOT signed for release). Report intra FF hold PER REGION with go15 (die_sta_related reports only the worst; a per-region
table needs a small script over the pair list).
