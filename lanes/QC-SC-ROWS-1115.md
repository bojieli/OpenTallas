# QC-SC-ROWS-1115 (2026-11-15 11:25 PST): sc family station rows

MEASURED placed dumps (S4Q2/S4P kits, tools placed_scan.py): slw_sc_v3 a10, sle_sc_v1__cl115da35f a10 (2 of 9 types; slw_sc_v1__cl64543eaf__cl4590432d a10/a5 on epyc10/epyc9 not scanned: same family). Zero-logic bin/bout <-> u_core hops over 405 um, NO station row in S4q3b / S4q4c:
- core -> bout_x_fe_o 48b 664-790 um; bin_x_fe_i -> core 47b 654-771 um; core -> bout_x_ctl_o 119b 496-511 um; bin_flt_fe_i -> core 1b 761-884 um.
- residual, NOT covered: x_ctl_i ring -> bin 160b (30-36 bits 405-652 um, cland ring class), bin_x_ctl_i -> core 3-4 bits 441-462 um, u_rrl_N reset relay -> bin/eq 690-995 um (1 bit each, reset relay), PIN:strap legs (strap exempt).
INFERENCE for the 7 types with no dump: same face/core geometry (generator uses outline + hard core box; pin->core-edge distance reproduces the dump: x_fe_i 771 vs 771, x_fe_o 790 vs 790, x_ctl_o 502 vs 511).

Rule: per bus x_fe_i, x_fe_o, x_ctl_o, flt_fe_i: face pin -> nearest point of u_core box, stations = ceil(d/400)-1, evenly spaced; input rows add a cland_bin_sites u_bin row at mid first hop (QC-FWST form). Lane bumps: fixed_cycles += src+dst station count (same as gen_fwst).
Result: 9 types, 34 rows, max hop 395 um (was 790); 46 lanes bumped (39 x +1, 7 x +2).
Files: lanes/qc-sc-rows/gen_sc.py (BASE_PLAN BASE_SIDECAR OUT_PLAN OUT_SIDECAR OUT_ROWS; runs on S4q3b or S4q4c, additive to the fe rows), lanes/qc-sc-rows/sc_rows_s4q3b.json (rows, lane_bumps, sidecar).
Gate runs: epyc9 /srv/opentallas-scratch2/claude/qc-sc-rows-1115 (tree = hardlink copy of treeA; plan zz_s29_qc103_s4q3bsc): bind chain S4Q3BSC (BR -> derive -> BQ + LATCHECK) via ot-run --priority plan, G0 g0_sc. Gate stamp follows.

## Update 12:41 PST: whole family (COORD: three classes + fe)
Measured (third dump slw_sc_v1__cl64543eaf__cl4590432d S4P a10): x_fe_o 788, x_fe_i 770, x_ctl_o 511, flt_fe_i 1041 um: matches the generator inference within 1 percent.
1. First bind S4Q3BSC FAILED (101 x KIT_ISTATION_LATENCY: latency table stale). Fix = gen.py latency --inplace after the rows (46 lanes changed, nothing else). QC-FWST/S4q4c do this already; any adopter must too.
2. x_ctl_i (ring -> bin 30-36 bits to 652 um, bin -> core 3-4 bits to 462 um): one station row + u_bin at mid first hop (route 527 um, hops 263). Now in gen_sc.py (5 rows/type, lanes bumped 58).
3. Reset relay hops (u_rrl_N 690-1041 um): ROOT CAUSE = every ot_dp_st of an sc type (u_bin_*, u_bout_*, u_ft_*_o_*) takes rst_n = rst_n_t0, ONE copy at the core tap (264.6, 997). Fix = existing reset.consumer_localization (reset_consumers.localize, never used before): each consumer > 405 um from tap 0 moves to the nearest published tap relay of EQUAL depth on clk (0 cycles, same clock, release cycle unchanged => recovery/removal hop <= 405 um, S81 seam lesson). gen_rst.py: 9 types, 535 rows, every consumer <= 405 um after. Bind fails closed if depth/clock differ. NOT proven by STA yet: needs the kit place (the new copy must land on the sink clock leaf).
4. fe family (placed dumps sle_fe_v1__cl1cbb7497 a12, sle_fe_v1__cl8210183c a15, sle_fe_v2 a12; S4q4c rows checked against every group): all measured core/pass-through legs are covered by QC-FWST rows EXCEPT x_fw_p1_o (core.chu -> bout up to 1040-1085 um, 0 rows, needs 2 stations, 8 types) and sle_fe_v2 st_wi (ring -> bin 844-947 um, 0 rows, 1 station). gen_fe.py + fe_rows_s4q4c.json (13 lanes +1/+2) on S4q4c. slw_fe types and sle_fe_v3: inference from the sle dumps by bus name (no placed dump).
Binds (epyc9, ot-run --priority plan): S4Q3BSA = x_fe/x_ctl_o/flt rows, latency fixed (running); S4Q3BSB = all sc rows (ctl_i + reset localization) (running, G0 g0_sb). Both on epyc9 because the hardlink tree is there.
