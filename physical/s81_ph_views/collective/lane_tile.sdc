# CLAUDE S81-PH coll v2 lane tile (dsfd_coll_lane_w / _e): appended after the calibrated margin IO SDC (core_clk = ck).
# tf = forwarded clock (kept buffer of ck), not a data output; rs = asynchronous stream reset (synchronised in the tile);
# chb = static configuration pin (registered in the endpoint).
set_false_path -to [get_ports {tf*}]
set_false_path -from [get_ports {rs* chb*}]
# tx leaves WITH its forwarded clock tf (inverted ck): the first die station captures tx on tf's falling edge = the
# next rising edge of ck, so the die clock-arrival term is 0 ps on setup (BUDGETS README: forwarded-clock hops) and the
# hold check is half a cycle away at the station (timed in die-context STA, not as a vclk hold at this pin:
# coll_lane_w 34b3e75dd FF -128 on tx was that vclk model).
set ot_tx [get_ports -quiet {tx[*]}]
if {[llength $ot_tx]} {
  set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2}] -clock vclk $ot_tx
  set_false_path -hold -to $ot_tx
}
