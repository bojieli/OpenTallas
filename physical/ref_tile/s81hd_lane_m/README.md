# s81hd_lane_m (HD-CTLGATE, S81-HEAD 10-21) -- MAIN

Head-die lane block `ot_s81hd_lane` (rtl/dsrom_sys/s81_head, HD-CTL b4f571642; 13 per head die: 6 TP4 mesh, 2 host,
5 draft) as a FLAT leaf: `dsfd_coll_lane_w_safe8_ntf` (the S81-COLL s8nr/s8nq lane: same sources, defines
OT_COLL_NATIVE32/_OFF, 55-SRAM macro map at the same coordinates, W SerDes face, k-means regional CTS) + the static
core adapter (valid-only core side; 3-flit TX buffer bit-sliced into 35 kept 16-bit slices with replicated control;
credit sender; always-accept RX pin flops; sticky would-overflow faults).  Flat because the safe8_ntf lane has no
CLOSED view yet (s8nq/s8nr routes live, S81-COLL): one hard block per head-die lane, nothing to bind below it.
Outline 812.16 x 583.2 = the s8nr lane body 725.76 x 583.2 + a 86.4-um E adapter band.  SerDes pins rx/tx on W
(as s8nr), core pins tx_v/tx_d/rx_v/rx_d/flt + ck/rst_n/chb on E (opposite face).  K = 32 regional roots.

Benches (Verilator 5.050, results/rtl/s81_head_ctlgate_1021/lane/): tb_s81hd_lane = two lane blocks, SerDes
loopback A.rx <- B.tx / B.rx <- A.tx, static schedule (<= 1 frame / 2 cycles) with CRC-corruption windows (replay):
6,504 / 6,493 flits bit-exact in order, no adapter fault, mean tx_v -> rx_v 29 cycles; then A off-schedule (tx_v every
cycle) -> A flt[3] sticky, B clean: PASS.  Mutants OVF (overflow never flagged) and RP (TX read pointer sticks) FAIL.

SAFE review (8 points, owner 10-19/10-21 checklist):
1 pins: PASS. Inputs land in pin flops (tx_d txd_p; tx_v / lo_r 2 kept ot_s81hd_kf copies each, <= 18 slices per
  copy), outputs leave flops (rv_q / rd_q / flt_q); rx enters the lane rx landing flops, tx = gearbox registered beat.
  Reset: rst_n -> ot_rst_relay_tree3 (root + group = 2-stage landing, 38 leaves <= ~32 reset pins), reset_landing 2.
  Faces: W 1,026 pins / 583 um (1.8/um), E 1,113 / 583 um (1.9/um).
2 reach: PASS (by structure). The lane is the s8 REACH=2 structure (relay hops + RX FIFO write landing, the s7 GRT reach
  fix); the adapter is per-16-bit slice, each slice local to its pin span; adapter -> lane lo_d is one flop->flop hop
  across the 86.4-um band.  The gate wire_reach / GRT audit measures it.
3 fanout: PASS. HD-CTL hard-child census max 32 (adapter); s8nr lane census max 32; flat census on the mapped
  netlist: see "Census" below.
4 depth: PASS. Adapter = one 3:1 AND-OR read mux + 4-bit counters per stage; lane unchanged (closed-structure depth).
5 storage: PASS. Lane FIFOs/replay in 55 SRAM macros (unchanged); adapter TX buffer 3 x 553 = 1,659 b < 2 kb in
  flops with one-hot pointers (no runtime-indexed array > 2 kb).
6 floorplan: PASS / fill waived. Macros on the 43.2 lattice (s8nr map, >= 20-um channels); one full-height std-cell
  region; fill ~15 % = channel area of the lattice-bound SRAM map (fill_reason), aspect 1.39:1.
7 clock: one region, k-means regional roots K=32 under a balanced top tree (the s8nk/s8nq/s8nr fix for the
  perimeter pin-flop ring); spread <= 80 ps TT+FF measured by the --cts gate; io_hold_margin 0.03.  Die crossings
  ctl <-> lane are land-plan rows (HD-CHAIN).
8 schedule: static. Flow control only at the off-die SerDes boundary (lane credits); the core side is valid-only, the
  ctl TX spacing keeps <= 1 frame / 2 cycles, an overflow is a sticky fault, never a stall.  Added cycles: TX
  tx_v -> lo_v 5 edges, RX li_v -> rx_v 1 edge (HD-CTL README, in the head schedule).

Census (pre-gate, flat, yosys 0.68 + ABC ASAP7 RVT TT, rtl/dsrom_sys/s81_head/test/hd_census.sh with HD_HARD=""): PENDING (fleet run cenflat_lane, recorded by the pickup)
