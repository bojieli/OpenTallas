# CLAUDE S81-PH coll v2 core tile (dsfd_coll_core): appended after the calibrated margin IO SDC (core_clk = ck).
# rs = asynchronous stream reset (synchronised in the tile).
set_false_path -from [get_ports {rs*}]
# v4 (CLAUDE 2026-10-07): engine reset release u_core.erst_n (fanout = every engine flop; v3 post-CTS recovery -681 ps)
# is a 3-cycle multicycle: the core holds the engine input until 3 cycles after the release (eg[3] in
# ot_s81ph_coll_core), so no engine flop changes state in that window (design intent as rst_mcp2).
set ot_erst {}
foreach ot_c [get_cells *] { if {[string match {*erst_n*} [get_full_name $ot_c]]} { lappend ot_erst $ot_c } }
if {[llength $ot_erst]} { set_multicycle_path -setup 3 -from $ot_erst; set_multicycle_path -hold 2 -from $ot_erst }
