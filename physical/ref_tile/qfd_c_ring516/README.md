# qfd_c_ring516 -- CB16 hardened landing-ring crossing tile (QW-CB16REG 10-20, main line a)

One CB16 region crossing as one closed tile: writer ring qfd_c_land_w1k (ck_w, source region) + reader qfd_c_land_r1k (ck_r,
destination region, incl. its output register), W=516, D 4, K 2 (rtl/physical/qcluster/qfd_c_ring_t.sv). Hardened once per
width; 12x in the CB16 parent (69 crossings). Function / epochs / latency identical to the soft pair (0 added cycles).
Bench tools/qwen_cluster/bench_ring_t.sh (Verilator 5.050, 20000 cycles, every output bit vs its cycle model and vs the soft
pair; K=3 mutant must FAIL); witnesses results/arch/qw_cb16reg_1020/bench/.
r0 gate (108 x 64.8, 10-20 22:38 ep5): WARN only (util 26%), TT/FF pin-flop spread 12.4/11.6 ps, setup +288 ps, hold +52 ps,
census max 31, GRT overflow 0. Now 108 x 43.2 (util ~35%).
## Safe-design checklist (owner 10-19)
1 Pins: PASS -- i -> 4 bank slot registers (flop-first), o = reader output register (flop-last), rsi_w/rsi_r -> kept reset
  copies (19 loads); ck_w + i + rsi_w on the S face, ck_r + o + rsi_r on the N face (parent may mirror MX).
2 Reach: PASS inside (108 x 43.2). Parent legs source -> tile and tile -> destination planned by tools/qwen_cluster/ring_tile_place.py.
3 Fanout: write enable 31 loads, vld per 30-bit super-group, rsi 19 loads; census max 31 (r0 gate).
4 Depth: reader = registered one-hot AND-OR over 4 slots; writer = enable mux.
5 Storage: 4 x 516 ring as flops (fixed rotating pointers, constant-index read; no runtime-indexed array).
6 Floorplan: 108 x 43.2 (21.6 multiples), 516 data pins per face on 103.7 um (<= 6/um); no macros. Pin-bound: util below the
  45-65% guidance (waived, pin-bound crossing tile).
7 Clock: two leaf CTS roots ck_w / ck_r (related, phase 0); the bank -> reader crossing stays inside the tile; parent delivers
  ck_w / ck_r from region roots balanced to one target. io_hold_margin 0.03.
8 Schedule: static; 0 added cycles.
