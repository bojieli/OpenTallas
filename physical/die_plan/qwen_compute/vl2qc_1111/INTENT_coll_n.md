# INTENT coll_n (VISLAYOUT2-QC, 2026-11-11)

Outline 786.24 x 786.24, kept. The strip width is set by the serdes PHY depth, and the faces are fixed. Positions only; no cycle change.

## Dataflow
- N face: serdes rx/tx, 597 b each, x 4-256, to and from the io_serdes PHY.
- rx: N → rx mem (64x546) → codec ctl → codec banks b0..b3 (64x512, r2c2) → S face rec_tx_s0_i (548 b) and flt/fltv_o (x 234-238) → coll_ftn (coll_f5, SIGNED; its S pins are not touched).
- tx: S rec_rx_s0 → codec → tx mem → N.
- Netlist trace (core_conns_netlist, a7 1_2_yosys.v):
  - the codec banks talk only to each other (r_addr / rd_out);
  - rx and tx connect to glue only;
  - no pass-through bundle crosses the type.

## Timing cause (routed a7, s15, NOT SIGNED: TT -197.55, FF hold -64.31 on 1329 endpoints)
- Setup: u_codec.u_ctl.epoch_abort (clk_serdes) → u_bout_fltv_o (clk).
  - Launch insertion is 594 ps, from the ot_edge_chain_clk_serdes staircase: the tap is at (423, 406), the sinks are in the NW.
  - About 510 ps of wire runs from the codec ctl, in the NW macro block, to the S-face fltv window.
- Hold: u_tx.ra → u_tx.u_mem r_addr_in.
  - The SRAM rclk comes through a separate long edge chain, clk_serdes_m0 (466 ps), against 351 ps on the flop tree: 115 ps of skew.
  - Also u_bin_rec_tx_s0_i → u_tx.wd at -38 ps.
- Picture: in the a7 final render, all logic sits in the W/NW, with heavy vertical routing in a 20-um channel between the two macro columns. The rest of the outline is about 75% empty.

## Hand arrangement (plan_vl2_colln_c, delta_colln_c.json)
- Macros: one W column at x 112.32, rows in dataflow order with a 95.04 pitch. From the top: rx, tx, then b2, b3, b0, b1 (the codec sits nearest the S face).
  - SRAM pins are on M4 at the W/E edges. The W edge faces a macro-free channel 112 um wide. The E edge faces the open glue column x 291-786.
  - No macro pin edge faces another macro or a face band (AMENDMENT 2).
- Glue column x ~300-786: a straight N-S macro-free channel for the serdes↔codec↔rec flow (AMENDMENT 3).
- Clock and reset:
  - tap_um and reset tap go to (328.32, 397.44), next to the codec rows; the count straps shift by -60.48 in x.
  - clk_serdes edge tap goes to (328.32, 561.6), beside rx/tx mem, so the SRAM rclk and the tx flop tree are fed from one nearby root (this addresses the hold class).
  - The face_s0 core tap moves to x 328.32. All taps are off the macros.
- One collector relay moves into the b3/b2 row gap: (196.56, 380.16) → (196.56, 388.8).
- Fallback if setup stays marginal: a declared +1 station on fltv_o, with a latency row.

## Scores (route_supply --grt-halving edge_outline, core_conns from the netlist)
| form | p99 | worst region |
|---|---|---|
| s22 as planned | 0.977 | street H |
| plan_vl2_colln_b (2 columns, 72-um channel) | 0.866 | — |
| plan_vl2_colln_c (adopted form) | 0.913 | street V |

- Form c is chosen over b because b points macro pin edges at each other and at the W face band (AMENDMENT 2).
- G0 diff vs s22: see the CLEANSLATE2-QC row.
