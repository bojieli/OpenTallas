foreach l [split $::env(PLIBS)] { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [get_clocks clk]
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -placement
report_checks -path_delay min -to [get_pins $::env(TO)] -format full_clock_expanded -fields {fanout cap slew}
