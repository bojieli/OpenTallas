# QC-CORES-2 btab r8 (qfd_dv_s8x_btab, 12 copies): no-pad tree + per-branch sizing + 12.8c trunk, 2026-10-27

COORD RULING BTAB-R7 (04:44): the r7 k6 tree padded L1 to T1 = 195.48 by detours (22 detour edges; planned 2771.3 um vs shortest 2149.2 um, excess 622 um, CHECKED from the r7 gate json). Re-plan with no padding, using per-branch sizing (12.8c / d1).

## Plan (all numbers PLAN MODEL uf_phys3 v1 = OT_PHYS_FIT results/model_refit3_1026/uf_phys3_v1.json, UNCHECKED)
- Same geometry as r7: r7 3_place, geo btab_m0_r7.geo (sha 4ea1d86d...), r7 Voronoi planner su_tree_uf_ls_r7.py (sha 0835df63..., OT_R7_BALANCE=0), leg keep-off 4.32.
- Gate: qc_su_prog_l1_1026/su_kit_gate.py --chain --straight L1,L2,L3 --phys --size (every edge drawn at its shortest legal length; su_branch_size picks node cells BUFx8..x24 by the gating predictor before build). Script plan/run_r8.sh.
- No-pad + sizing sweep (TT rise / FF early, window):

| k | islands (sinks) | no trunk TT w / FF w | verdict |
|---|---|---|---|
| 5 | 1032..305 | 197.8 w40.2 / 149.6 w34.9 | FAIL window |
| 6 | 844,357,631,500,314,796 | 187.6 w23.4 / 143.0 w21.8 | FAIL window (the r7 k6 islands cannot be balanced without padding) |
| 7 | 338,357,665,738,313,555,476 | 197.3 w13.0 / 149.6 w13.1 | windows PASS, mean shallow |
| 8 | 338,184,665,738,313,555,476,173 | 199.8 w12.6 / 151.8 w12.4 | windows PASS, mean shallow |

- The no-pad tree is ~50 ps shallow, so 12.8c applies: trunk_r8.py inserts ONE fixed entry trunk of n identical buffers between the root and its children. They sit on a column below the entry at a 1.08 um pitch, in the same form as core_family_slice.add_entry_trunk. (master, n) is chosen by the gating predictor: guard-band PASS first, then the smallest |TT-250|+|FF-202.5|.
- **Chosen k7 + 3 x BUFx16f: TT rise 256.13 w13.44 / FF early 192.70 w12.96, P_phys PASS** (guard TT 250+-9, FF 202.5+-10, window <=14). FF is 0.2 ps inside its guard edge, and the textbook sensitivity is dTT -6.8, dwTT +11.65, dFF +2.9.
  - k8 + 3 x BUFx16f also passes (258.31 w12.77 / 194.61 w12.66).
  - k7 was picked because its leaf-count spread per island is smaller (2-4 vs 1-4). That matters because MODEL-REFIT-3 found the GRT->RCX shift is about 3.2 ps per leaf.
- Detour: **0 of 90 edges, planned = shortest = 2512.1 um, 0.0 % of tree wire** (CHECKED from the gate json edge list). It used 14 L1 chain repeaters.
- COORD leg rule: 0 um of the legs run in the SRAM pin columns x224.42-239.54 over the macro rows, and 0 um run in the +4.32 keep-off (CHECKED, recomputed from edge_paths_um). G5 found 0 nodes in pin columns and 0 legs across SRAM.
- Render (viewed): btab_r8_k7_np_plan.png.

## Kit / build (intel1:/srv/opentallas-scratch2/claude/qccores2-btab-1027/btab_m0_r8)
- The r7 kit and r7 3_place are reused unchanged. The changes are OT_MSCTS_SPEC=mscts_spec_r8.tcl (= plan/btab_r8_k7_np.trunk.tcl, sha 05a3657e...) and PRE_CTS_TCL=pre_cts_r8.tcl.
- COORD RULING DRT-0255: ck, ft_ck_i and ft_ck_o are widened to 0.048 x 0.48 on their M5 tracks before CTS. The log line R8_CLKPORT reports all 3 at 0.048 x 0.480.
- Chain kit/chain_r8.sh runs CTS+GRT, then DRT, fill and 6_report (RCX), then the warm hold ECO (ELEM-QK recipe b, data-path only, 12.4a1), then signoff.py tt,ff, then main lec.py on the routed 6_final.v.
- Open risk: r7 DRT was data-only and ended with 768 violations at iteration 11 (M2-M4 shorts and eolKeepOut). 431 of them are in the SRAM gap / pin-column edge bin x220-240 y120-140, and about 270 are in the W channel x120-180 y120-160 (ptw_data). r8 keeps that placement. The SRAM pin-column halo flag (claude/qc-cores-1027-sramhalo) goes into r9.
