foreach l $::env(PLIBS) { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set f [open /probe/arr.tsv w]
foreach p [get_pins -hierarchical */CLK] { puts $f "[get_full_name $p]\t[get_property $p arrival_max_rise]" }
close $f
