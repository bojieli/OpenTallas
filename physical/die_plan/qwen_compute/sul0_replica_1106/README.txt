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
GRT results (11-06, intel1, both builds identical in shape):
  vA (PD 0.50): GRT-0116 after 30 iterations, overflow 131132 -> 1880 (M3 only, Max V 1).  It lists the same 4 reset
    relay nets (u_rrl_35 x 404.1, u_rrl_39 x 389.3, u_rrl_26 x 409.3, u_srl_26 x 351.1), 470 gcells each.
  vB (PD 0.40): GRT-0116 after 30 iterations, but overflow 131132 -> 1880 (M3 only, Max V 1).  The congestion report
    lists only 4 nets, each 470 gcells = one full lane height in one column:
      u_rrl_35 x 405.8 over lane0, u_rrl_39 x 395.6 over lane1, u_rrl_26 x 399.0 and u_srl_26 x 355.1 over lane3.
    These are reset relays (reset_tree.tcl rtr_place).  Tap relays sit in the lane gaps INSIDE the lane x-span
    (rst_n_t11 397.3/30.3, rst_n_t12 381.5/349.9, rst_rl_26 375.8/1317.6), so each relay net is a straight vertical
    across one macro.  The baseline already had them (u_rrl_26 / u_srl_26 / u_rrl_39 in its congestion.rpt).
    Not a bus net: zero c_i/c_p1 nets overflow.
    Probe (sul0probe/grtprobe1*.tcl): one such net alone still gives 470 capacity-0 gcells, even with only M6-M7,
    with the PDN swires removed and with the lane M5/M6 OBS removed.  So it is a single-column relay-net shape
    problem, not demand.
    Next form (reset_tree class, not part of this patch): site reset relays/taps outside the lane x-span (west strip
    x < 190 or east of x 605), or route the relay hop around the lane.

Reset relay form (11-06 follow-on, DIE-QC-85):
  Kit-local vC (vA + re-site) and vD (vC + PD 0.40), built on intel1 from the start (synth -> GRT).  Placement only:
  no RTL change and no cycle change.  rst_hopfix.py moves 9 relay sites (18 with the u_srl copies) so that every hop
  has an L route outside the grown lanes.  Relay order, depth, kind, the lane tap sites (lane rst_n pins: lane0 397.3/34.7,
  lane1 381.5/354.3 south face, in their own channel) and the reset_tree.tcl hop list are unchanged.
    u_rrl_33 609.1/539.9 -> 609.1/300.0    u_rrl_34 470.8/306.7 -> 609.1/30.3    (lane0 tap u_rrl_35 from the south channel)
    u_rrl_37 470.8/626.4 -> 609.1/600.0    u_rrl_38 470.8/626.4 -> 609.1/349.9   (lane1 tap u_rrl_39 along the lane1 south face)
    u_rrl_25 470.8/1041.1 -> 185.8/1041.1  u_rrl_26 375.8/1317.6 -> 185.8/1317.6 (west mouth, then north strip to u_rrl_27)
    u_rrl_28 565.8/1041.1 -> 609.1/1100.0  u_rrl_29 -> 609.1/1317.6  u_rrl_30 470.8/1317.6 -> 400.0/1317.6 (east strip, north strip)
  Estimate: crossing hops 8 -> 0 (4 raw + 4 run nets), max hop 380.0 um (plan reach), no relay inside a grown lane box.
  Plan image sul0_reset_vC.png (viewed): before (red = crossing) / after.
Class rule (tools/die_plan/reset_tree.py resite_crossing / resite_type / native_resite_sites; plan
  reset.relay_resite_crossing is OPT-IN, default false: absent or false gives the pre-11-06 trees.  DIE-QC-85 11-06:
  the QC plan is frozen fix-only).  A hop with no L route outside every grown blockage moves the free relays of its
  chain (single child, not at a tap) between the fixed anchor above and the fixed node below.  They go onto the
  shortest obstacle-avoiding rectilinear route (Hanan grid of the grown faces), spaced so that each hop is a <= 1-bend
  sub-path <= plan reach.  The graph is unchanged and a tree without crossings comes back identical.  Unresolvable
  hops are left as they are and reported.
  su_l0 use (the only enabled use): captured native trees are never re-solved.  native_resite_sites(tree, boxes,
  box_out, paths) gives the sites-only bound_reset_placement overlay (bound_reset_contract.placement, needs a PASS
  image review) for slw_su_l0__cl76fb247e / __cl1a1c1f8f / __cl1e5219ea.  On the captured cl76fb247e tree it resolves
  all 4 crossings (moves u_rrl_24/25/26, 28/29/30, 32/33/34, 36/37/38, max hop 380).  The vC kit uses the
  hand re-site above (same intent, fewer moves).
  CANDIDATE FOR COORD RULING (not enabled): with relay_resite_crossing true on qwen_compute die_plan.json, 5 of 65
  non-hard types would change reset sites: slw_su_l1 7, slw_su_c 6, sle_su_l1 8, sle_su_c 4, native59 2 relays.
  The current plan su_l0 trees (30/31 relays, grid topology) have no crossing.
  Tests: test_reset_tree.py (4 new: su_l0 resite, no-op + native overlay, unresolvable report, opt-in flag) and every
  die_plan test that imports reset_tree: 452 passed.  test_check.py::test_run_keeps_plan_path_for_plan_relative_files
  fails on the base too (gen_phys S.Plan.rect).
vC / vD results (11-06, intel1):
  vC (replica + reset re-site, PD 0.50): GRT-0116 after 30 iterations, overflow 1880 -> 940 (M3 470 + M7 470, Max V 1).
    No reset net overflows any more.  Only 2 nets are left, both u_bout_x_su_c_p1_o (the 369-b output bin: D from lane3
    w_u_lrly3_*, Q to the west M6 ports at y 262-338), each a straight vertical over lane2 (x 350.0 and 571.7,
    y 725.6-992.9, 470 gcells).  This is the same class: a register net joining the lane1/lane2 gap to the lane2/lane3
    gap.  Candidate next form: site u_bout_x_su_c_p1_o FIRM in the west strip at the lane3 channel mouth (sul0_sites
    mechanism).  Its D nets then run west along the lane3 south channel and its Q nets down the west strip, so no
    net crosses a lane.
  vD (vC + PD 0.40): stopped at the post-CTS structural hold gate before GRT.  FF register-to-register wns -340.65 ps
    is beyond the -260 stop, and it is 1 path only: u_bound.u_cland_origin/s0 -> s1 (launch clock 151.7 ps, capture clock
    578.1 ps; 426 ps of skew on one landing-origin flop).  Not a reset or bus net.  vA/vB/vC had register-to-register
    above the stop (port-only advisory).  Probe: dq85sul0/probe/hgprobe_vD.log.
vE (11-06, intel1): vC kit + face OUTPUT registers sited at their source lane channel mouth.  Placement only: RTL,
  istations.tcl and every u_bin replica site are byte-identical to vC (checked).  Rule 4 in sul0_apply.py, so all 3 types:
 4. bout rule.  For each `ot_dp_st u_bout_<B>` (q = output port bus), a D bit is sited when (a) a placed macro output
    drives it from a SOUTH or NORTH pin (west-edge pins already sit on the strip), and (b) the straight pin -> port segment
    crosses a macro gap to gap.  Its q flop goes FIRM at x = macro x0 - 3.6, in the channel the pin faces (south pin =
    channel below the macro, north pin = channel above it).  The rows continue after the bin replica columns.  Then the
    D net stays inside its channel, and Q is mouth -> port along the west strip.  East-edge sources are reported
    (other_edge), not sited (0 here).
  Check of every bout/bin on the vC 4_cts.odb (probe/bxcross2.py, nets of each register's cells that cross a lane gap
  to gap): every u_bin replica 0, x_ctl_o 0, x_sc_o 0, x_stm_o 0, x_su_c_o 0, flt_o 0.  x_su_c_p1_o: 19 nets cross lane2.
  These are repair_design wire-buffer chains: lane3 south pin (x ~450, y 1045.5) -> buffers at y 996 -> y 723 -> ... ->
  q flop near its port (x 6, y 308).  The geometric rule sites more bits than were measured crossing, because the
  same geometry holds by construction in all 3 types:
    x_su_c_p1_o 340/369 (lane2 177, lane3 163), x_ctl_o 343/456, x_stm_o 172/228, x_sc_o 32/38, x_su_c_o 44/452;
    931 bout flops in total.  Channels: lane0/lane1 gap 203 (2 columns), lane1/lane2 gap 760 bin + 364 bout (4 columns),
    lane2/lane3 gap 760 bin + 364 bout (7 columns, x 179.3-186.5).
  Estimate (sul0_bout_est.py): straight segments crossing a macro, lane pin -> port before = 931, after
  (pin -> site + site -> port) = 0.  Image sul0_bout_vE.png (viewed): every vE segment stays in its channel or in
  the west strip.
