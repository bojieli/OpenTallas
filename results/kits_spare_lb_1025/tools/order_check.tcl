foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
set p [get_pins {mul.wp[83]$_DFF_P_/CLK}]
estimate_parasitics -placement
set_propagated_clock [get_clocks clk]
puts "OT_DISC A est-then-prop arrival [get_property $p arrival_max_rise]"
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
puts "OT_DISC B prop-then-est arrival [get_property $p arrival_max_rise]"
