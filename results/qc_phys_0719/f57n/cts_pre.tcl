source /work/hold_budget.tcl
estimate_parasitics -placement
repair_design -max_wire_length 80 -slew_margin 20 -cap_margin 20
detailed_placement
uplevel #0 {
source /work/mscts_core.tcl
ot_ms_build
# Uniform physical NDR for the clock trunks; no per-tap timing assignment.
set tech [ord::get_db_tech]; set du [$tech getDbUnitsPerMicron]
set widths {}; set spaces {}
foreach ln {M5 M6} {set l [$tech findLayer $ln]; lappend widths $ln [expr {2.0*[$l getWidth]/$du}]; lappend spaces $ln [expr {2.0*[$l getSpacing]/$du}]}
create_ndr -name f57n_2w2s -width $widths -spacing $spaces
set nd [$tech findNonDefaultRule f57n_2w2s]
if {$nd eq "NULL"} {error "f57n missing physical NDR"}
foreach n [[ord::get_db_block] getNets] {if {[string match ot_ms_* [$n getName]]} {$n setNonDefaultRule $nd}}
}
