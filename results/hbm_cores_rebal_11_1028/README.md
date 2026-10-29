# HBM-CORES-REBAL-11 (2026-10-28) -- C24 kits: lanes_plain canon, programme_store_r10, hnx_lane_x

Plan: DIE-HBM-10 C24 (intel2:/srv/opentallas-scratch2/claude/die-hbm-10/c24, die_plan sha 3ab76af4), c24_side.json
core_arrays (REBAL-6 dr_lp/dr_ps plan-fixed SRAM arrays + driver_rects) and core_views (hnx_lane_x child view).
Work dir intel2:/srv/opentallas-scratch2/claude/hbm-cores-rebal-11 (kits/, preflight/, post_{lp,ps,hnx}/).

## Kits (all KIT_PREFLIGHT PASS 0, CHECKED; receipts *.txt here)
| kit | form |
|---|---|
| lanes_plain__canon_663526_717c67b4174a-_c24_m5w1gr | oneclk delta (lp_oneclk.py = REBAL-4 lanes_oneclk.py, MOD swapped; 76 clock alias bits -> scalar clk_bank, 3754 non-clock pins identical), MLAT5/WCOPY1 wrapper, C24 array (24 SRAMs) + 8 driver_rects (max detour 19.1 um), REBAL-10 keep + copy guides (g_wcopy, 15 um) + relay guides (relay_lanes_canon.json: 12 groups resolve) |
| programme_store_r10_20117b319f18-_c24 | C24 array (44 SRAMs 512x256) + 16 driver_rects (max detour 87.4 um) |
| hnx_lane_x_c17b412817f2-_c24 | mk_hnx.py: C24 side view (285.12x302.4, 1670 pins) appended to the views table; slice in mk_c20 form at the centre clk pin (island 138.24,146.88..+8.64; 12.8b grid 2x2, 5 islands); recipe = hnx_rp3lp3h_n recipe with the leaf replaced by the REBAL-5 lane-cut file, top hnx_lane_x, no SRAMs; --face-shell off (inputs land on station flops, output is the registered gather: a shell would add a cycle per crossing and break the proven cut) |

Estimate before build (UNCHECKED model 1.0-1.15 ps/um + 151 ps hop overhead, budget 773 ps): lanes_plain relay hops
<= 344.9 um -> worst +225..+277 ps; copy -> own SRAM inside the 15-um guide.

## Shared fix (ROOT-MERGE): master_slice.check_kit judges driver_rect islands at their driver site
The first preflight of both array kits FAILED (fail_pre_dr_fix receipts kept on intel2): master_slice.check_kit required
every mp_isl<k>_* cell inside the island rect, but REBAL-5's merged opt-in driver_rect (7cc88eeba0, core_infra) places
the drivers at driver_rect_um by design. Fix: pushdown_cell_issues() judges an island with driver_rect_um against that
rect; islands without it are judged exactly as before (same message). No new check. test_master_slice +1 test;
test_master_slice + test_core_infra + test_master_plan PASS.

## Hand trial runs (ot-run intel2, GOAL cts, --mem 32) + chain_r11.sh (3_place ideal TT STA + render, 4_cts propagated)
Collect post_{lp,ps,hnx}/{status,sta_3_place.log,sta_4_cts.log,3_place.png,4_cts.png,hold_gate.log}; renders must be viewed.
After the shared fix is on main, enqueue the finish through the autopilot (--goal finish --mode trial); the hub preflight
uses main's master_slice, so lp/ps cannot pass admission before the merge.

## SU (8) / SFU (2) slices
sbind_canon (die-hbm-7, 10-28) asbuilt_sources.json still aliases ot_hbm_su_static_pgslice_lg -> _s and
ot_hgi_sfu_core_split3 -> _sp2 (bind as tap + stub / 1 cell); no full-RTL manifest exists -> ASK DIE-HBM.
