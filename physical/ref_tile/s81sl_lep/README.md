# s81sl_lep -- S81-SLICE3-LEP structural successor (10-19)

Top ot_s81sl_lep (HOST_EN 1, s_7N). RTL 23fd77ae5 (branch claude/s81-slice3-lep-1019): ot_s81sl_lep_core TXRP 1 + RXSA 1 (both opt-in in the core,
ON in the plain leaf tops; MU tops unchanged). Outline 475.2 x 475.2 (primary).

Why a redesign: lep route 90fc20580 NEEDS_RTL TT -44.76 and the d77e88ef6 regate FAILED (TT pin-flop spread 84.8 > 80,
real reg->reg -58.97 ps g_rx[0].g_c[0].g_on.rpc[0] -> 8:1 head-row mux -> h0[3:1] decode -> 514-bit g_hrx.fh_d enable;
the same cone selects the 1,103 rid bits); lepnh route 90fc20580 TT -55.92 (TX SRAM rd_out across the lane-0 column)
and its fx3 regate FAILED (TT spread 90.1). Previous floorplan: macros off the 43.2 lattice (31.104 / 226.824),
std cells in inter-macro slivers, clock entry at the SW corner.

## SAFE-DESIGN checklist (owner 10-19), pre-gate; the gate packet re-checks 3 / 6 / 7 on the actual placement
1 Pins: PASS -- every port source-registered (ro -> rov/roq, li -> vq/dq, lo/ri/li_r/rxv/fault/f_* leave flops);
  pin_reg_split (one launch flop per output pin, fixes the DFFE f_host/f_ks pin flops); reset_landing 2 stages.
2 Reach: PASS -- TX: roq -> wd_q (WREG) -> SRAM and SRAM -> odr (TXRP, beside the column) -> od pin flop: every
  single-cycle leg <= ~260 um (column x 43.2..433 vs W/E faces); RX: dq -> group slices -> hd -> rid / fh_d all in the
  rows between the macro rows; no leg crosses the tile twice.
3 Fanout: FIXED -- RXSA: 18 column groups (<= 31 bits) per lane, each with kept one-hot slot-enable (wg), head
  pointer (oh) and pop (pc) copies; rid select 35 kept copies (<= 32 bits), fh_d 17, fk_d 2. Kept regs, not
  keep_hierarchy modules (no paramod rename issue); the gate's keep check must find g_g[*].g_on.{wg,oh,pc} and
  g_sr[*].g_on.sr in the netlist. Remaining wide fanout: rov (1 pin flop -> 1,104-bit frame AND, resizer tree, 2 levels).
4 Depth: FIXED -- head row from flops (show-ahead hd), consumer selects from flops: rid / fh_d / fk_d = 1 AND or
  enable mux after a flop; next-state cone (n_nx -> rel_nx -> kind_nx mux -> select D) ~8 levels.
5 Storage: PASS -- TX 2 x 512 x 553 in 10 ot_sram_1r1w_512x128 macros; RX DR 8 x 553 x 2 in flops (8 rows,
  registered one-hot slot enables, no runtime-indexed read: one-hot AND-OR per group).
6 Floorplan: FIXED -- macros on the 43.2 lattice: columns x 43.2 / 259.2 (centre channel 41.9 um), rows y 43.2 .. 388.8 at 86.4 pitch, all R0; every macro gap >= 20 um and
  >= 41 um to every pin face; full-width standard-cell rows between every macro row and along N / S (each a
  full-width band, PDN-connected, no islands). Pins: W lanes lo/li + l*_f/l*_st (NW corner 453-472), E ro/ri, N host plane (703 pins), S clk/rst_n/sl_f/fault; W/E <= 4.9/um (<= 6/um), full faces. Aspect 1:1.
  WAIVED with reason: util 23-27% (pin-bound by the W/E faces + lattice/channel-bound) and "ONE central band":
  the SRAM's signal pins sit on its W/E short faces (SYMMETRY X Y, no rotation) and TX read is clk->q 421 ps TT, so a
  single central band would put the far macro rows 190-450 um from their read register (fails item 2); the sister
  S81-MUBUF3 cut analysis (s81sl_lepmua_b64 GPL NaN, _sf DPL) reached the same conclusion. Known open (shared SRAM
  owner): macro-face contact density ~10/um on the macro's own W/E faces.
7 Clock: FIXED -- clk enters the S face centre (235-239 um, in the centre channel between the two macro columns, beside the
  RX / select register mass), km16 regional roots (clock_split_km); judged on pin-flop spread <= 80 ps TT and FF
  (gate); io_hold_margin 0.03, hold_margin 0.045. No hard children.
8 Schedule: static on-die. TXRP +1 edge on lo0/lo1 (lo_v/lo_d; credit round trip ~8 <= CRED 8: full beat rate, the
  elastic off-die boundary absorbs it); RXSA 0 edges; reset release +2 (landing). Handed to lanes/MU-DIE-S81.md INBOX.

Benches (Verilator 5.050, ot-epyc6 via ot-run, 23fd77ae5): lep s1/s7, lep_host s3/s9, lep_nhr s1/s7, lep_nh s5/s11
PASS; mutants swap/nopair/noovf/ksoff/hdrop/nhacc and new txrpv/rxsel/rxbyp FAIL. Witnesses
results/rtl/s81_slice3_lep_1019/.
