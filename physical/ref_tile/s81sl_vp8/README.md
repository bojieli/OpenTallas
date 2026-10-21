# s81sl_vp8 / s81sl_vp8_fb: ot_s81sl_vp r8 (ELEM-VP8 10-21, structural successor of r7 3efb91d8d)

Owner S81-ELEM / ELEM-VP8. Same outline (734.4 x 864.0), pins, macro / hard-lane lattice as r7 (s81sl_vp / _fb).
MAIN `s81sl_vp8` (ER=2 IR=1 XR=1); FALLBACK `s81sl_vp8_fb` (define OT_S81SL_VP_RELAY: ER=3 IR=2 XR=2).

## Why (r7 pre-route STA on the r7 CTS odb, TT placement RC, signoff.sdc)
1836 violating endpoints, every one a single-cycle wire across the tile (no deep logic):
dop -> hw_v 1.27 mm (-209 ps), k_op / k_cv (N pins x~10) -> n_pre / m_* (+ pin copies, E y~500) ~1.03 mm (-178),
si -> hr_* (-168), hqd_c (E pin) -> lane feed lr ~0.98 mm (-92), hqv_c -> k_hsv / src1 (-85), dsi1 -> k_cfe beside the
lanes (-79), q0/q1 -> hw_d (-47), x_ra / x_w* (W pins) -> bank addresses ~0.96 mm (-105).
Clock: boundary pin flops 1137..1228 ps TT (92) / 97 FF > 80: count-bisection spine padded every flop leaf with 8 HB4
cells (~380 ps) up to the hard lanes' insertion target.

## Fix (RTL rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv; static schedule, no handshake; compiler-visible latencies)
- E seam outputs (hw_*, hr_*, n_go/n_pre, m_*, wl_*): core flops beside their sources + ER kept relay stages to the pins.
- h round trip: hq pin flop + IR kept relays (one chain to the banks / fault, one per lane COLUMN, 64 b), y row / valid
  pipe YD = 3 + ER + IR, HSTORE valid line 5 + ER + IR.
- lane feed (lrA / lyA / k_lanevA) and lane output (lo_r / lv_r / lf_r) relays in BOTH kits (r7: FALLBACK only).
- x extension port: request (x_rv / x_ra) pin flop + XR relays; write (x_wv / x_wa / x_wm / x_wd) pin flop + XR - 1
  relays + the kept per-group copies beside the banks.  x_qv / x_qd 4 + XR edges after x_rv (vs is x_qv-driven).
- POST coefficient capture re-registered beside the lanes (k_cfe2 / cfq): +1 internal edge.
- clock: symmetric insertion-aware spine (OT_SPINE_SYM / TREE_PAD / SAFE_BALANCE, tol 8, bins 30, 20 iters; as CLOSED
  qfd_d2d_static_r8): lanes tap the tree at their insertion node, flop leaves stop carrying ~380 ps of pad cells.

Latency ledger (MAIN / FALLBACK): E outputs +2 / +3; POST post_cmd_to_last_hw 63 -> 70 / 73 (bench); HLOAD / GAIN /
NORM / NORMR outputs +2 / +3; x read 4 -> 5 / 6 edges; x write lands +1 / +2; HSTORE bank write +3 / +5; POST -> POST
issue spacing +5 / +7 (coefficient overwrite vs the last lane issue). Slice calendar note when bound.

## SAFE review (8 points, ELEM-VP8)
1 pins PASS (unchanged): every input lands in a pin flop, every output leaves a flop; faces <= 1.1 pins/um; 2-stage reset landing.
2 reach FIXED: registered hops on every cross-tile seam: worst 1.27 mm -> 3 hops <= ~430 um (E), x 0.96 mm -> 2 hops
  (MAIN, within measured repeated reach 600-750 um) / 3 hops (FB), hq -> lane column 3 hops.
3 fanout PASS: r7 kept copies unchanged (native 32/0); relays 1:1, per-column lane chains drive 4 lanes; gate census decides.
4 depth PASS: no logic added; relays only split wires.
5 storage PASS: 2 x 512x128 SRAM macros on the lattice; write-back ring; y pipe 6 / 8 x 128 b (data-moving pipeline).
6 floorplan: outline slot-fixed (pins match the slice); ~+4.6k / +6.9k relay flops (util ~0.36 -> ~0.40, gate measures)
  spread into the 58 um lane channels: the top band no longer carries every cross-tile wire in one segment.
7 clock: one region (0.73 x 0.86 mm, < 1 mm), symmetric spine; pin-flop spread <= 80 TT+FF judged by the --cts gate;
  every former >~0.6 mm single-cycle crossing is now a registered relay hop.
8 reset: control / valid only (relay valids on leaves 15 / rs_c; data relays and the E output relays unreset, flushed
  while reset is held >= ER edges).
