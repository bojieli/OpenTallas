# qfd_c_ring516 -- CB16 hardened landing ring tile (QW-CB16REG 10-20, main line a)

One CB16 region crossing as one closed tile: qfd_c_land_w1k (ck_w, source region) + qfd_c_land_r1k (ck_r, destination
region), W=516, D 4, K 2 (rtl/physical/qcluster/qfd_c_ring_t.sv). Hardened once per width; the CB16 parent instantiates it
12x (69 crossings). Function/epochs/latency identical to the soft pair (0 added cycles).
## Safe-design checklist (owner 10-19)
1 Pins: PASS -- i -> 4 bank slot registers (flop-first), o = reader output register (flop-last), rsi_w/rsi_r -> kept reset
  copies (1 + NGS = 19 loads); clocks ck_w (S face) / ck_r (N face).
2 Reach: PASS -- tile 108 x 64.8 um; no wire > 405 um.
3 Fanout: PASS by construction (qfd_c_land_k: write enable 31 loads, vld per 30-bit super-group, rsi 19 loads); in-flow census
  (limit 32) re-measures on the mapped netlist.
4 Depth: PASS -- reader = registered one-hot AND-OR over 4 slots; writer = enable mux.
5 Storage: 4 x 516 ring kept as flops (fixed rotating pointers, constant-index read; < 2 kb per slot, no runtime-indexed array).
6 Floorplan: 108 x 64.8 (multiples of 21.6), 516 data pins per face on 103.7 um = 4.98/um <= 6; no macros; full std-cell area.
7 Clock: two leaf CTS roots (multiple_cts_roots, related same-frequency, phase 0); the bank -> reader crossing stays inside the
  tile; parent delivers ck_w / ck_r from region roots balanced to one target. io_hold_margin 0.03.
8 Schedule: static; 0 added cycles vs the soft pair.
