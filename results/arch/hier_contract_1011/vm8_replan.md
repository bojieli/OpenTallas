# VM8 top-down re-plan (vm8cp, 2026-10-12)

Generator `physical/hbm_accel_die_views/vm/cp/make_vm_cp.py` (writes the RTL, the composition `hfd_vm_cp.sv`, the 19
ref_tile specs and `budget.json`, which is the machine-readable form of this page). Bench: `run_vm_cp.sh` (Verilator 5.050).

## 1. Why the old partition failed

Over r3-r11, 36 grid sub-tiles (8 halves x 3x2) failed in a different way on almost every tile: corner-pin DRT-0255;
GPL-0305 at 3.5% util; face pins at 9.4-12 b/um/layer; a 25.7k-sink core tile; GRT-0183 on crossing nets
(`f_w_wr__t[*]`); DRT stuck at 577-6,686; and TT/FF misses on input->D wires. The cause is the partition itself:

* About 85% of a half's flops only carry wires from one place to another. In sw_e, there are 86k sinks, and root_x accounts for 10.7k of them.
* The ring buses are fixed at 2,264 / 2,256 / 256 bits per direction, 9,552 b per quadrant link and 38k b over the 4 links. Their live content is much smaller: 217-2,063 b of VM traffic, plus placeholder copies.
* Placeholder pass-throughs (`f_su_* -> t_su_* / t_quant / t_router`, with no VM function) cross the 1.4 mm VM, so they pass through every tile on the way.
* The grid cut makes those feed-throughs turn corners inside 48-130 um wide tiles. The result was 9.2k vertical bits on a 350 um row seam.

## 2. Function to place (counted from make_vm_tiles.py / hfd_vm.sv)

| stream | bits | from -> to |
|---|---|---|
| root write data | 2,048 | f_su_SW (SW W face) -> root |
| root write request | 217 | f_su_NW[216:0] (NW W face) -> root |
| root read request | 201 | f_su_SE[200:0] (SE E face) -> root |
| cfg serial | 1 | f_su_NE[0] (NE E face) -> root cfg chain (772) |
| published row | 2,063 | root -> xSW, xNW, xSE, xNE (same row, 4 faces) |
| status | 202 unique (970 pins) | root -> t_su_SW[969:0] |
| slice cmd / wd / return | 10 + 768/768/768/512, 1 + 768/768/768/512 | root <-> 4 slices (6/6/6/4 macros) |
| placeholder | 2,048 / 2,048 / 2,048 / 1,078 | f_su_SW -> t_su_SE, f_su_NW -> t_su_NE, f_su_NE -> t_su_NW (+t_quant, t_router subsets), f_su_SE[1077:0] -> t_su_SW |
| q faces | 580 + 2 fclk | local to each die face |

## 3. Floorplan

The VM region is 1,399.632 x 2,000.112 um: the union of the 4 r22 quadrant slots, with its origin at the hb_vm_sw origin.

* There is no parent route. The die places 25 tiles built from 19 kits (two-level hierarchy).
* Logic is a compact cluster at the centre-left: the root, plus 2 slices below it and 2 above it.
* Every bus runs in die-level channels through registered relay tiles. A relay tile has one flop per bit, with D on an input pin and Q on an output pin. It has no logic and pins on two opposite faces.
* The placeholders use a bottom lane and a top lane with 4 relays each. They never enter a logic tile.

| tile (kit) | x, y (um) | w x h (um) | contents | sinks |
|---|---|---|---|---|
| u_root (vm_cp_root) | 345.6, 777.6 | 302.4 x 432 | root_x SEATP=1 FREG=1, cfg 772, out regs 2,265; no read-assembly hold (slices equal-latency) | ~13.7k |
| u_s0 / u_s2 / u_s1 (vm_cp_slice3, x3; s1 MX) | 345.6/604.8, 540 and 1231.2 | 259.2 x 216 | 6 SRAM + cmd/rd regs | ~1.6k |
| u_s3 (vm_cp_slice2, MX) | 604.8, 1231.2 | 172.8 x 216 | 4 SRAM | ~1.1k |
| u_fw0..3 (vm_cp_fw0..3) | 0, k*499 | 10.8-17.3 x 498.96 | W die face: pin flops, forks, q face | 3.1k-5.7k |
| u_fe0..3 (vm_cp_fe0..3) | 1386.7, k*499 | 10.8-13.0 x 498.96 | E die face | 1.1k-4.1k |
| u_rb0,1,3 (vm_cp_rb) / u_rb2 (vm_cp_rb2) | 172.8/518.4/864/1209.6, 172.8 | 15.1-21.6 x 302.4 | bottom lane (+rd fork N) | 3.1k |
| u_rt0,1,3 (vm_cp_rt) / u_rt2 (vm_cp_rt2) | same x, 1468.8 | 15.1 x 388.8 | top lane (+cfg fork S) | 4.1k |
| u_rwa / u_rwb / u_rwt | 129.6; 475.2 / 1274.4 / 734.4 | 13-15 x 259 / 108 / 518 | W channel: wr data, wr req, tap fork + status fan-out | 2k / 0.2k / 5.1k |
| u_re (vm_cp_re) | 950.4, 806.4 | 21.6 x 388.8 | E channel: tap fork to xSE/xNE, rd + cfg into the root | 4.3k |

Every tile has its own clock root, and no tile exceeds 15k sinks. Relay and face tiles are sized from 0.62 um2 per bit at util 0.45; the pre-route gate checks this and reports the real std area. Pins are on M4/M6 (W/E faces) and M3/M5 (N/S faces). PG is M7 stripes, so signals use M2-M6. Every pin sits at least 2 um off the tile corners: each port has a range (ref_tile `pin_ranges`, new), placed on the end of its face nearest to its neighbour.

## 4. Crossing budget (peak over a 10 um window, b/um/layer)

The worst face is **5.79** (u_rwt W: 5,096 b / 518 um), and no face is above 6.0. The densest faces are rwt W 5.79, fw2 W 5.71, rb2 N / re S 5.71 (201 b on 21.6 um), root W 5.66, rwt E 5.66, re E 5.37, rt E/W 5.32, rb 5.24, root S 5.18.

There are 52 die-level hops. The longest is **477 um**, measured pin-range mid to mid: rb3 -> fe1 460, rt3 -> fe2 447, rt0 -> fw2 446, re -> fe1/fe2 442, rb0 -> fw1 434. Each hop is one registered stage.

Interior bits compared with the old plan:

| crossing | old plan | new plan |
|---|---|---|
| quadrant links | 4 x 9,552 = 38,208 b through tiles | — |
| placeholder lanes | (inside the links above) | 3,126 b (bottom) + 4,096 b (top), in channels |
| functional, W side | (inside the links above) | 5,298 b |
| functional, E side | (inside the links above) | 2,266 b |
| root <-> slices | (inside the links above) | 5,676 b, adjacent tiles |

## 5. Cycles

These depths are checked by the bench.

* Write port: 2 flops from the die pins for every field (FW0 -> RWa, FW3 -> RWb), one depth.
* Read port: 3 flops (FE0 -> RB2 -> RE), one depth.
* Tap row: root out reg -> RWt/RE -> face = 3.
* Placeholders: face + 4 lane relays + face = 6.
* Slices: command and return latency are identical for all 4. A read returns from all 4 in the same cycle. A sim `$fatal` guards this, because the r19 2,816-flop hold is removed.
* Extra cycles relative to the monolith only change path latency; the bench mode 2 table lists them.

## 6. Contract changes (die lead)

* The 4 quadrant slots are replaced by one VM region with 25 die-placed tiles. The slots' outer die faces are unchanged (W: SW/NW, E: SE/NE).
* Pins move within their faces as follows: SW W face, f_su/i/q in y 0-499 and t_su/xSW in y 499-998; NW W face, xNW/t_su_NW in y 998-1497 and f_su/i/q in y 1497-1996. The E face mirrors this.
* **t_quant moves from the NW N face to the NW W face (y 998-1497). t_router moves from the SW W face to the NW W face (y 998-1497).**
* The VM die top routes 52 tile-to-tile hops of 477 um or less in channels that are at least 100 um wide.

## 7. Route risk per tile

| tile | risk | why |
|---|---|---|
| root | medium | The only real logic tile: 13.7k sinks, root_x seat/SECDED paths with FREG=1 (closed before inside sw_e tiles). Inputs reach root_x without pin flops (WARN-tier boundary). Utilisation depends on the gate std area; resize the outline to it. |
| slice3 / slice2 | low | 6/4 SRAM with 20 um channels and registered macro I/O. The same slice closed inside the r19 tiles. |
| face tiles fw/fe | low-medium | One flop per pin with no logic, at 4-5.7 b/um/layer. They are thin (10.8-17 um) and 499 um tall, with forwarded-clock bits on x/q (forwarded_clock subtree). Watch placement on very narrow outlines. |
| lane relays rb/rt | low | Pure flop columns at 5.2-5.3 b/um/layer. Inputs and outputs are on opposite faces, so nothing turns inside a tile. |
| rwt / re | low-medium | Fork tiles at 5.4-5.8 b/um/layer, the densest faces in the plan. |
| rb2 N / re S (201 b on 21.6 um) | medium | 5.71 b/um/layer on M3+M5. If DRT struggles, widen these two tiles to 32.4 um. |

Old r9-r11 jobs stay live (not cancelled). The two plans do not mix within a quadrant: the old halves talk over the ring buses, the new tiles over channels. If a whole quadrant closes first on the old plan (both halves: all tiles + the 5.050 composition bench), it is kept, and an adapter is needed at its 2 seams; otherwise vm8cp replaces the open halves.
