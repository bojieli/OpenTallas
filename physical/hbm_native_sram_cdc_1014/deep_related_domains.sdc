source /src/physical/hbm_native_bounded_cdc_1014/related_domains.sdc
# Actual TT source-root R315.9/304.3 in predecessor CTS; use deep pair S210/H100.
# No native clock delivery or corner compensation is inferred.
foreach {ot_from ot_to} {core_clk vm_clk vm_clk core_clk} {
 set_clock_uncertainty -setup 210 -from [get_clocks $ot_from] -to [get_clocks $ot_to]
 set_clock_uncertainty -hold 100 -from [get_clocks $ot_from] -to [get_clocks $ot_to]
}
