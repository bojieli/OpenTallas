# qfd_coll_split_q9a -- Q leaf successor of q8a/q8b (QE3-COLL 10-21; q9a MAIN / q9b FALLBACK gated in parallel) -- MAIN

q8 verdicts: q8a FAIL GRT-0183 net42538 = W-face SerDes capture srr_q2 bit19 (pin flop at the W face) driving its
xsrc/g_out mux on the far side of the W SRAM stack (route across the macro wall); q8b FAIL GRT-0183 net10846 at the
SRAM W pin wd59 (sink GCell M2-M5 full) on a 24-nm seam to the abutted bank, plus clock 115.8/114.3 > 80.
Root cause (both): two-column abutted SRAM stacks (pairs/triples abutted, 10.8-um halo on all four sides, so the
"cut" channels held ~1.4 um of rows) = 83-110-um walls with SRAM pin faces packed against each other's seams.

Structural change (RTL, ports, faces, clock, reset unchanged; zero cycles):
- 3 macro columns instead of 2 walls: W = u_sd 4x256 (MY, read data faces the centre) | centre = u_rring/u_pring
  4x128 | E = u_xf dr banks 4x128 (R0). Every macro free-standing: NO abutment anywhere.
- halo split: wide on the SRAM pin faces (W/E), 2.16 um top/bottom (no pins) -> every N-S gap between SRAMs is a
  real std-cell crossing row (>= 20 um), the longest SRAM run is one 41-um macro.
- std-cell channel >= 20 um beside every SRAM pin face (W strip, both column channels, E strip) for the data-pin escape.
- W/E 128-bit buses 4 pins/um over 128 um centred on the mid crossing; SerDes inputs sr1/sr2 (E: dp/dr) in the
  middle, so the capture flops land beside the xsrc mux with no SRAM between them (q8a fix).
- outline at the 35 % owner fill floor (gen/gate FAIL < 35 %): the enlargement goes into channel width, not slack.
Geometry: 248.40 x 276.48 um (fill 35.2 %), pin-face halo 10.8 / top-bottom halo 2.16, std channels 20.4 um (W strip, 2 column channels) / 20.7 um (E strip), N-S crossing gaps 21.3 um (sd column) / 22-48 um (ring/xf columns), no band.

## SAFE-DESIGN checklist (QE3-COLL)
1 Pins: RTL registers every pin (pin_regs opt-out unchanged); W/E 4 pins/um, N/S <= 1.3 pins/um -- PASS
2 Reach: tile <= 286 um per side; every registered hop < 405 um by construction -- PASS(geom)
3 Fanout: RTL unchanged from q7/q8 (census max 32; gate native_census re-checks) -- PASS
4 Depth: native LAT7 adder 288 ps / 9 levels; q8a placement worst reg->reg +68.7 ps -- PASS
5 Storage: 12 SRAM macros on the 0.432/2.16 lattice, rows between every macro (no abutment) -- PASS
6 Floorplan: fill 35 % (owner floor), every pin-face channel >= 20 um std, N-S crossings >= 20 um -- WARN fill only
7 Clock: same balanced symmetric spine (OT_SPINE SYM/SAFE_BALANCE/MACRO_LEAF; q7 33.7/34.6, q8a 40.2/37.9) -- CHECK at --cts gate (q8b 115 was the abutted geometry)
8 Reset/schedule: r4 reset (one face leaf + 2 relays), static schedule, zero added edges -- PASS
Benches: unchanged RTL; q7 bench5b witnesses (gold unit 13 / prod 4 PASS, 6 mutants FAIL incl RERR) carried in job.json.
