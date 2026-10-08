# Qwen ROM die masters: margin-route kit (owner margin-first rule, 2026-10-06)
One route per die master. Route over-constrained at 770 ps; sign-off at 833.333 ps = slack@770 + 63.333 ps
(single-corner tools/w18/corner_sta_ref.py, SS setup / FF hold, 60 / 25 ps uncertainty). Accept SS >= +40, FF >= +15.
Boundary: 0.2 T (166.667 ps) outside budget, referenced post-CTS to this block's propagated clock (a boundary
register, OT_REF_GLOB), plus the die clock-arrival difference: OT_IO_SKEW (90 ps, same clock region) on every port,
OT_IO_SKEW_INTER (150 ps) on the ports in OT_IO_INTER (cross a die wire to another clock region); hold allowance
OT_IO_HOLD_SKEW 50 ps, closed by hold repair.  Files: <master>.sdc (plain, loaded by every ORFS stage), io_plain.sdc,
io_ref_skew.sdc, pre_cts_skew.tcl / pre_ref_skew.tcl / post_plain.tcl (QDM_SDC_DIR), macro_place_tile.tcl,
jobs/route.sh.
