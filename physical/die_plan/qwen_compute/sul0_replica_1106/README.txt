DIE-QC-85 / DQ85-SUL0 11-06: su_l0 per-lane bin replica form (slw_su_l0__cl76fb247e, __cl1a1c1f8f, __cl1e5219ea).
data_cycles 0, plan geometry unchanged (no pin, macro or interface move). COORD ruling 15:4x (replicas per lane),
64-um gap rebalance dropped by DIE-QC-85 (it moves the clk_c2/clk_c3 interior die-spine pin = parent interface).

Cause (measured on kw21 attempt_3 of cl76fb247e, epyc5): GRT-0116, overflow M3 55933 / M5 4699 / M7 70500.
- u_bin_x_su_c_i (766 b) and u_bin_x_su_c_p1_i (765 b) are BROADCAST face registers.  All four lane macros read
  them (600/600/571/504 and 160/160/189/256 bits; c_i = 760 bits per lane).
- Lane c_i pins: lane0 and lane1 are on the WEST edge (M4).  Lanes 2 and 3 are on the SOUTH edge (M5) at the same
  die x 310-470.  The RSMT of each broadcast bit therefore joins the lane2 pin to the lane3 pin straight over
  lane2, where only M7 is free (lane OBS M1-M6).
- 4_cts.odb: 568 nets have pins on both sides of lane2 (552 with every pin east of x 250, buffers at y~722 / ~1000).
- Probe (sul0probe/grtprobe.tcl): a GRT of ONLY those 568 nets (81013 other nets dropped) needs 24 congestion
  iterations but ends with 0 overflow (M7 0.44%).  So M7 over lane2 is usable, and the M7 PDN and OBS are cleared
  as causes.  In the full run every listed overflow is Vertical over lane2 at x 250-300 / 450-600, beside the pin
  range: the crossing bus plus its repair-buffer clusters in the lane2/lane3 pin channels compete with the lanes'
  own pin-access nets, and the spill goes over the macro (M7 only; M3/M5 capacity 0 there).
Form (sul0_apply.py, run on a fresh kit before the flow; for all 3 types it produces the same replica widths and sites):
 1. Each bin whose q is read only by >= 2 placed macros is split into one ot_dp_st replica per reading macro,
    holding exactly the bits that macro reads.  Same clk, rst, D bits and epoch input.  Lane port bits are re-pointed.
 2. Replica flops are placed FIRM through istations.tcl -> sul0_sites.tcl -> ff_put_near at x = macro x0 - 3.6 um.
    WEST-edge pins: at the pin y.  SOUTH-edge pins: a 3-5 column block (1.2 um) over the lane's own south channel.
    Every D net then branches only in the west logic strip, and every Q is a 2-pin net along its own channel.
    No net joins two lanes over a macro.
 3. Estimate: lane3 channel (51.8 um) carries ~983 nets west (760 c_i Q + c_o) vs ~1350 derated M4+M6 tracks
    (~73%) + M2.  Lane2 channel 103.7 um ~37%.  The west strip (190 um) carries the vertical D trunks:
    1531 nets vs ~8500 derated V tracks.
Proof (sul0_eqproof.py): yosys miter of the bin -> lane c_i slice, gold vs replica (async2sync, sat -tempinduct):
  "Induction step proven: SUCCESS!"  The mutant (sul0_apply.py --mutant: 2 swapped D bits in the last replica)
  gives "model found for base case: FAIL!".  The bound diff is limited to the u_bin, q decl and u_laneN lines.
  The flow LEC (lec.py) runs on the kit as usual.
Builds (intel1, ot-run; epyc6 refused, scratch below floor): kits
  /srv/opentallas-scratch2/claude/dq85sul0/slw_su_l0__cl76fb247e_{vA,vB}  vA PD 0.5, vB PD 0.40.
GEOM (vA 3_place, viewed): sul0_place_vA.png.  The replica blocks sit at the channel mouths (x 182-188).  The D-trunk
  buffers of l2/l3 stay in the west strip (x < 190).  Nets with pins on both sides of lane2: 568 -> 18 (17 are the
  pre-existing u_bout_x_su_c_p1_o output bus, 1 clk).
