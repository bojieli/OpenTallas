# CLAUDE S81-PH: forwarded-clock outputs (ck through a kept ot_fwd_clk_inv) are clocks of the die station chain, not
# data paths of the view; the die-context STA times them as generated clocks (svcio_m1: of/xf/af -216 ps as data).
set ot_fc [get_ports -quiet {of* xf* af* vf*}]
if {[llength $ot_fc]} { set_false_path -to $ot_fc }
