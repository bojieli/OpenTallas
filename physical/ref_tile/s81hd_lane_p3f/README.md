# s81hd_lane_p3f (STW-S81c-HEAD-LANE 10-22) -- FALLBACK: 898.56 x 799.2, core face N (H10 core_i/core_o face), adapter L-band (E 129.6 + N 172.8)

ot_s81hd_lane as a CLUSTER under the RELEASE FREEZE (owner 10-22 00:02: ports / widths / link timing contract unchanged; RTL
unchanged = claude/s81-head-h10-1021 2331b6cec lineage).  Hard child u_ln = CLOSED view dscoll_lane_w_s8ng
(dsfd_coll_lane_w_safe8_ntf, default CORE_CRED 8 = this instance; closure-loop dscoll_lane_w_s8ng-s8ng-8151c3923 TT +9.95 /
FF +6.81 / DRC 0; head-branch lane source differs only by the opt-in CORE_CRED parameter, default-identical) at (43.2, 43.2)
R0.  Parent = the static adapter (35 kept TX slices, kf pin copies, RX pin flops, reset landing + tree3, rxen) on a balanced
spine targeted at the child's routed boundary insertion (child_clock_ref boundary: TT mean 698.4).
Predecessor flat m/f: clock_rule FAIL (one 24.1k-sink root over 812 um, boundary spread TT 81.5/FF 83.0 m, TT 112.9 f).
Two-root flat successor p2 (+ck_l port) was stopped at freeze (interface change) -> NEXT-RELEASE (branch
claude/s81-head-lane-p2-1021 @ce199999b).

SAFE review (8 points):
1 pins: PASS. Core pins land in / leave RTL flops (txd_p, kf copies, rv_q/rd_q/flt_q); rx/tx/chb are wires to the child's
  own pin registers (lr landing, gearbox beat).  Densities: core 1,113 pins / ~580 um (1.9/um); W 1,026 / 573 um (1.8/um).
2 reach: adapter <-> child E face = one flop -> flop hop across the 129.6-um band (<= ~200 um, p3f <= ~600 um from the N
  pin flops via slices: pin flop -> slice -> ld, 3 registered hops); child = closed REACH 2 structure.
3 fanout: PASS (adapter census max 32: kept slices / kf copies; child closed native census).
4 depth: PASS (adapter 3:1 AND-OR read mux + 4-bit counters; m/f depth 548.4 ps).
5 storage: child SRAMs inside the closed view; adapter 1,659 b < 2 kb in flops.
6 floorplan: child on the 43.2 lattice with a 43.2-um ring; adapter band; fill child-bound; never shrink.
7 clock: the lane's 19.7k flops are on the child's own closed tree (boundary spread TT 73.5 / FF 67.6 routed); the parent
  tree serves only ~4.7k adapter flops in one band, spine-aligned to the child boundary mean -> pin-flop spread target
  <= 80 TT+FF (single ck port, frozen).  Region crossing child <-> adapter = register -> register.
8 reset/schedule: reset only control/valid; static, flow control only at the off-die SerDes; 0 cycles changed.
Die: slot_change_request (reserve 518.4 x 1123.2 -> this outline; the child cannot rotate).
