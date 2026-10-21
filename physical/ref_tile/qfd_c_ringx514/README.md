# qfd_c_ringx514 -- CB16 hardened landing-ring crossing tile (QW-CB16REG 10-20, main line a)

One CB16 region crossing = this tile (writer ring qfd_c_land_w1k on ck_w + the reader's slot select on ck_r; W=514, D 4, K 2;
rtl/physical/qcluster/qfd_c_ring_t.sv) + one closed station qfd_c_stn514 on ck_r at the destination (= the reader's output
register). Hardened once per width; 57x in the CB16 parent (69 crossings). tile + station == qfd_c_land_w1k + qfd_c_land_r1k
(bench tools/qwen_cluster/bench_ring_t.sh, Verilator 5.050, 20000 cycles, every bit vs cycle model and soft pair: PASS;
mutant K=3: FAIL 39945 errors; witnesses results/arch/qw_cb16reg_1020/bench/). 0 added cycles.
History: r0 single-tile form (writer + reader + output register, 108 x 64.8) gated WARN 10-20 (spread 12 ps, setup +288 ps,
GRT ovf 0) but could not be placed in the parent (one tile must bridge source -> destination: CP-SAT infeasible below ~600 um
reach) -> split at the reader's output register (three <=405-um legs as the soft plan).
## Safe-design checklist (owner 10-19)
1 Pins: region-crossing tile (owner 09:05: pin regs at crossings): i -> 4 bank slot registers (flop-first); o = the reader's
  slot select (bank regs ck_w + one-hot/warm regs ck_r -> 2-3 gates) registered by the parent's closed station on ck_r;
  rsi_w / rsi_r -> kept reset copies (19 loads). No in->out combinational path.
2 Reach: tile 108 x 43.2; parent legs source -> tile, tile -> station, station -> destination planned <= 405 um
  (tools/qwen_cluster/ring_tile_place.py).
3 Fanout: write enable 31 loads, vld per 30-bit super-group, rsi 19 loads; gate in-flow census limit 32.
4 Depth: select = AND-OR over 4 slots; writer = enable mux.
5 Storage: 4 x 514 ring as flops (fixed rotating pointers, constant-index read; no runtime-indexed array).
6 Floorplan: 108 x 43.2, 514 data pins per face on 103.7 um (<= 6/um); no macros. Pin-bound: util ~30% (guidance waived).
7 Clock: two leaf CTS roots ck_w / ck_r (related, phase 0); bank -> select inside the tile; io_hold_margin 0.03.
8 Schedule: static; 0 added cycles.
