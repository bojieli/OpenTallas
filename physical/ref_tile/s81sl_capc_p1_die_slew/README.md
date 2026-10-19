# s81sl_capc_p1_die_slew (S81-CAPC, 2026-10-19)

Electrical successor of routed CAPC a62 (`s81sl_capc_p1_die_rc_order-s81capc_die_rc_order-a62cd1284`: timing CLOSED
TT +326.31 / FF +17.43, DRC 0, own routed native PASS 114.7/113.2, PG connected) whose exact final TT electrical report
had two max-slew violators (receipt 38183aece, `results/rtl/s81_slice_1017/capc_nativep1_1019/routed_a62/`):

| pin | slew / limit | net | driver -> load | span | routed R / C |
|---|---|---|---|---|---|
| `_1653_/A` | 300.71 / 260 ps | net2389 | pin reg `g_pin.wq[27]` QN -> BUFx3 `place2390` (8,36) -> INVx1 `_1653_` (25,176) -> child `u_tw/rt[27]` | 157 um, 1 load | 4.96 kOhm / 27.2 fF |
| `place2292/A` | 275.63 / 260 ps | nd[0] | child `u_rt/cw_n_d[0]` ETM output (175,160) -> BUFx3 `place2292` (205,265) -> out pin reg `cw_n_d[0]` | 135 um, 1 load | 4.25 kOhm / 24.6 fF |

Cause (measured on the a62 CTS ODB with the new gate probe): the resizer's default wire limit left 677 single-driver
signal nets of 120-165 um; the 30 % slew margin at placement / GRT RC did not cover routed RC on two of them.

Fix (structural, no waiver): `orfs_vars POST_RESIZE_TCL=physical/common_flow/max_wire_repeat.tcl` runs
`repair_design -max_wire_length 80` (OT_MAX_WIRE_UM) after the ORFS 3_4 repair, so every signal net is a short driven
segment (child ETM outputs get a repeater within 80 um of the pin); repeaters on a hard child are snapped just outside
its halo (no global re-placement: gate 1 @71a296754 used post_resize_relocate.tcl, whose incremental GPL re-spread all
cells -> max net 220 um, 45 slew violators after CTS, gate FAIL; the new gate check caught it).  Spec `max_signal_net_um: 100` makes the gate FAIL on any single-driver net > 100 um; the gate
also FAILs on any max-slew violator after CTS (tools/ref_tile/path_classes.tcl GATE_SLEW / GATE_LONGNET).
Everything else is the a62 kit byte-for-byte (RTL ot_s81sl_cap_p1 PINPIPE=1, outline 345.6 square, child origins, clock
spine, hold budget die, io_hold_margin 0.03, signoff.sdc, pins).  Only kit.env EXTRA gains the two orfs_vars.

## Safe-design checklist (owner 10-19)
1. Pins: PASS (RTL PINPIPE=1 registers all 721 input + 451 output bits; reset 2 registered stages g_pin.rst_l0/l1).
2. Reach: PASS (a62 routed stage pairs max 386.651 um <= 405; this kit only adds repeaters).
3. Fanout: PASS (a62 census max signal fanout 14 through BUF/INV/HB4; keep_pin_regs on).
4. Depth: PASS (unchanged RTL; no comb in->out; a62 TT setup +326 ps).
5. Storage: PASS (no new storage; children are the closed hard views).
6. Floorplan: PASS/WARN (children on 43.2 lattice, full-width 43.2 um south std band; fill 39 % < 40 % is the a62 WARN:
   outline fixed by the closed children, no growth).
7. Clock: PASS (centre-fed spine on the south band; a62 own spread 43-47 ps TT/FF; hard-child boundary refs; io_hold 0.03).
8. Schedule: PASS (static; repeaters add no cycle; the +2 edge PINPIPE capture / reset +2 obligation is unchanged and is
   owed by the parent / die schedule, see lanes/MU-DIE-S81.md).
