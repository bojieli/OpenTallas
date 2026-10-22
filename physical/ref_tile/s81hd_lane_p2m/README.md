# s81hd_lane_p2m (STW-S81c-HEAD-LANE 10-22) -- MAIN (outline = the H10 die reserve ln_* 518.4 x 1123.2)

Head-die lane block `ot_s81hd_lane` (13 per head die: 6 TP4 mesh, 2 host, 5 draft) = `dsfd_coll_lane_w_safe8_ntf` u_ln (the
CLOSED dscoll_lane_w_s8ng lane structure, CRED 8, unchanged) + the static core adapter, flat leaf, **two regional CTS roots**.
Successor of s81hd_lane_m/f (agidock 10-21 09:26): native/GRT 0/setup +59/+65/hold +44/+49 PASS, but clock_rule FAIL =
boundary (pin-flop) spread TT 81.5 / FF 83.0 ps (m), TT 112.9 (f) on ONE ck root over an 812-um tile whose pin flops sit on
both opposite faces; and the 812.16 x 583.2 outline never fitted the H10 die reserve (518.4 x 1123.2).  Not a retry: new RTL
port + two roots + portrait floorplan.

RTL (rtl/dsrom_sys/s81_head/ot_s81hd_lane.sv, this branch): +input ck_l; u_ln.ck and the rx-enable flop on ck_l; nothing
else changed (git history 2331b6cec -> this: no unit dropped).  Every ck <-> ck_l crossing is register -> register: adapter
slice ld -> lane core landing (u_ski relay/landing flops), lane sender u_sko li_v/li_d -> rv_q/rd_q, lane lo_r -> u_cr kept
copies, lane flt -> flt_q, reset leaf r_lane -> lane rs relay, r_misc -> rxen (async assert, release timed).  STA times the
seam as related same-frequency roots (clock_data_paths related_same_frequency, phase 0): a fixed-latency landed crossing,
0 added cycles.  Bench (Verilator 5.050, ck_l = ck): base PASS 6504/6493 flits exact, overflow flagged, stats identical to the
one-root block (sent 7504/6493, mean latency 29, flt 1000/0000); mutants OVF and RP FAIL (caught) --
results/rtl/s81_head_lane_p2_1021/lane/.

Floorplan (518.4 x 1123.2): lower block = the s8ng map at its CLOSED coordinates (gearbox 10 x 32x64 at x 43.2, replay 18 x
256x64 at x 129.6-302.4, y 43.2-559.8), SerDes rx/tx on the W face 2.16-576.72 exactly as s8ng; RX FIFO 18 x 256x64 above
(4 columns x 43.2-302.4, rows 626.4-972.0 (18 of 20 slots, top row centre pair)); core landing u_ski 9 x 32x64 column at x 432.0 straddling the replay/FIFO seam (y 388.8-751.7); adapter band under
the N face y 1013-1123 (110 um) + the E strip x 470-518 above u_ski.  Faces: W rx/tx/ck_l/chb (SerDes neighbour; MY for the E-SerDes lanes), N tx_d/tx_v/ck/rst_n/rx_v/flt/
rx_d (H10 core_i/core_o face): N 1,113 pins / 518.4 um, W 1,028 pins / 586 um.

SAFE review (8 points, owner 10-21 checklist):
1 pins: PASS. Every data pin lands in / leaves a flop in RTL (pin_regs off with reason); recipe-2 io_flop_at_pins anchors
  the pin flops at their faces (4 cols).  Densities: N tx_d 553 / ~250 um = 2.2/um, rx_d 553 / ~250 um = 2.2/um (<= 4);
  W rx 514 / 286 um = 1.8/um, tx 512 / 286 um = 1.8/um.  Reset: rst_n -> kit 2-stage landing at the N face (ck) ->
  ot_rst_relay_tree3 (leaves <= 32); lane region reset = its own tree3 below r_lane (landed crossing).
2 reach: by structure as s8ng (REACH=2 relays: rx 2-stage landing, 2 forwarded frame hops gearbox -> RX FIFO control,
  RX FIFO write landing, core-face landing stage).  Portrait distances: gearbox -> FIFO <= ~700 um (2 forwarded hops, as
  s8ng 430-640 um), adapter -> u_ski <= ~600 um through the core-face landing stage, u_ski -> replay <= ~450 um.  The
  gate wire_reach / GRT reach audit measures it (classify any > 405-um single-cycle pair before the next variant).
3 fanout: PASS. HD-CTL adapter census max 32 (kept slices / kf copies); s8ng lane census max 32; flat native census at
  the gate (old m/f gates: native OK on the same netlist).
4 depth: PASS. Same netlist as m/f (depth 548.4 ps measured by textbook_lint, setup +59/+65 ps routed TT).
5 storage: PASS. All lane arrays in the 55 bank64 SRAMs on the 43.2 lattice, >= 20-um channels (min 23.4 um at the seam,
  45 um between 256x64 rows, 52-95 um between columns); std cells in every channel; adapter 3 x 553 b < 2 kb in flops.
6 floorplan: PASS / fill pin-bound 11-13 % = channel area of the lattice-bound SRAM map inside the die reserve; outline
  never shrunk (FB enlarges).  Macro-edge via guard on (recipe 2) for the s8ng SRAM-edge M4 DRC lesson.
7 clock: TWO CTS roots (multiple_cts_roots): ck (core region: N band, ~4.7k flops, entry N centre) and ck_l (lane body,
  ~19.7k flops, entry W y 580 beside the SerDes pins = centre of the lane region's pin-flop column).  Each root's pin
  flops lie on ONE face (W 586 um column / N band) -> per-root spread target <= 80 TT+FF (old one-root spread came from
  W-vs-E faces 812 um apart).  Region crossing = the register -> register seam above; die: both roots from one PLL phase 0,
  ck_l neighbour-matched to the SerDes, ck to the ctl links (landed-regions standard).
8 reset/schedule: reset only control/valid (adapter data unreset, lane as s8ng); static schedule, flow control only at the
  off-die SerDes boundary (lane credits), core side valid-only, overflow = sticky fault.  0 added cycles vs m/f.

Die obligation (HEAD die owner): connect ck_l (lane/SerDes region clock) on every ln_* instance; MAIN fits the reserve,
FB needs +86.4 um W-E.
