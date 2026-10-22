# qfd_coll_split_q10a -- Q leaf successor of q9a (SQ-C2-COLL 10-21; q10a MAIN / q10b FALLBACK gated in parallel) -- MAIN

Why: PD-AUDIT 10-21 C3 (owner MUST-DO): q9a W/E faces carried 558 pins in 127.7 um (4.4/um) clustered on 46 % of the face.
Structural change (RTL, ports, N/S faces, macros, outline, clock, reset unchanged; zero cycles):
- W/E 128-bit buses spread over the FULL face: 5.4..271.08 um, 66.42 um per bus = 1.93 signal pins/um (512 bus pins over 265.7 um; the gate's 558 count = 2.10/um); corner margin 5.4 um.
- Bus order bottom->top chosen from the RTL hop graph (pin flops are FIRM at their pins, io_flop_at_pins):
  W sx2, sx1 (outputs launched from internal pf/hi/lo regs, near the S-face sx0 launch) | sr2, sr1 (SerDes captures srr_q -> g_out -> od_q on the N face)
  E ur (from the xr ring), dp (-> lo/hi regs) | dr (drr_q -> od_q on N), up (upd_q <- ir_q on N) at the top.
- Worst pin-flop -> pin-flop Manhattan hop (any N bit position): 387 um (W sr2 / E dr -> od_q) <= 405; up_data <= 320 um.
  q9 centred order had up_data 451 um and sr1 419 um worst case (>405), so the reorder also removes a latent reach breach.
  Every other consumer of a W/E pin flop is a free std-cell register (xsrc -> u_xf input, lo/hi, pf_q, xr ring), no relay needed.
Geometry: 248.40 x 276.48 um (fill 35.2 %), q9a macros/halo (10.8 W/E, 2.16 N/S) byte-identical.

## SAFE-DESIGN checklist (SQ-C2-COLL)
1 Pins: RTL registers every pin (inputs land in exactly one flop, outputs leave a flop; pin_regs opt-out unchanged); W/E now <= 1.93 bus pins/um over 96 % of the face; N/S unchanged (<= 1.2/um) -- PASS
2 Reach: worst pin-flop -> pin-flop hop 387 um by construction (od_q / upd_q partners), internal regs free; no relay, 0 cycles -- PASS(geom)
3 Fanout: RTL unchanged from q7/q8/q9 (census max 32; gate native_census re-checks) -- PASS
4 Depth: native LAT7 adder 288 ps / 9 levels; q9a TT-place setup +29 ps -- PASS
5 Storage: 12 SRAM macros on the lattice, 3 free-standing columns, rows between every macro (no abutment), >= 20-um channels -- PASS
6 Floorplan: fill 35 % (owner floor; outline kept, not shrunk), pin-face std strips 20.3-21.2 um now carry the spread pin flops over the full height -- WARN fill only
7 Clock: same symmetric spine; q9a measured TT/FF pin-flop spread 37.2/34.3 (q9b 37.9/33.0) -- CHECK at --cts gate
8 Reset/schedule: r4 reset (one face leaf + 2 relays), static schedule, zero added edges -- PASS
Benches: unchanged RTL; job.json carries lint + coll_gold_unit (13) + coll_gold_prod + 6 mutants (expect fail) from q9a @304e340b0.
