# CLAUDE S81-PH svc IO r3 tiles: the od / xd / ad data outputs leave WITH their forwarded clock (of / xf / af: the first
# die station captures them on that clock), so their setup budget carries no die clock-arrival term (BUDGETS README:
# "forwarded-clock hops take 0 ps on setup"; sheet dsfd_svc_io: skew class fwd, 0 ps).  The margin SDC put 150 ps on
# them (svcio_od: SS +33 before / -25 after the output hold ECO).  Hold stays on the FF model (vclk_latency.tcl).
set ot_fo [get_ports -quiet {od[*] xd[*] ad[*]}]
if {[llength $ot_fo]} { set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2}] -clock vclk $ot_fo }
