# QC-SC-ROWS-1115 (2026-11-15 11:25 PST): sc family station rows

MEASURED placed dumps (S4Q2/S4P kits, tools placed_scan.py): slw_sc_v3 a10, sle_sc_v1__cl115da35f a10 (2 of 9 types; slw_sc_v1__cl64543eaf__cl4590432d a10/a5 on epyc10/epyc9 not scanned: same family). Zero-logic bin/bout <-> u_core hops over 405 um, NO station row in S4q3b / S4q4c:
- core -> bout_x_fe_o 48b 664-790 um; bin_x_fe_i -> core 47b 654-771 um; core -> bout_x_ctl_o 119b 496-511 um; bin_flt_fe_i -> core 1b 761-884 um.
- residual, NOT covered: x_ctl_i ring -> bin 160b (30-36 bits 405-652 um, cland ring class), bin_x_ctl_i -> core 3-4 bits 441-462 um, u_rrl_N reset relay -> bin/eq 690-995 um (1 bit each, reset relay), PIN:strap legs (strap exempt).
INFERENCE for the 7 types with no dump: same face/core geometry (generator uses outline + hard core box; pin->core-edge distance reproduces the dump: x_fe_i 771 vs 771, x_fe_o 790 vs 790, x_ctl_o 502 vs 511).

Rule: per bus x_fe_i, x_fe_o, x_ctl_o, flt_fe_i: face pin -> nearest point of u_core box, stations = ceil(d/400)-1, evenly spaced; input rows add a cland_bin_sites u_bin row at mid first hop (QC-FWST form). Lane bumps: fixed_cycles += src+dst station count (same as gen_fwst).
Result: 9 types, 34 rows, max hop 395 um (was 790); 46 lanes bumped (39 x +1, 7 x +2).
Files: lanes/qc-sc-rows/gen_sc.py (BASE_PLAN BASE_SIDECAR OUT_PLAN OUT_SIDECAR OUT_ROWS; runs on S4q3b or S4q4c, additive to the fe rows), lanes/qc-sc-rows/sc_rows_s4q3b.json (rows, lane_bumps, sidecar).
Gate runs: epyc9 /srv/opentallas-scratch2/claude/qc-sc-rows-1115 (tree = hardlink copy of treeA; plan zz_s29_qc103_s4q3bsc): bind chain S4Q3BSC (BR -> derive -> BQ + LATCHECK) via ot-run --priority plan, G0 g0_sc. Gate stamp follows.
