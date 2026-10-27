read_db /work/run/results/asap7/hc_ot_qwen_tp8_pv_join_t__172_8x172_8/base/3_place.odb
source /tool/core_infra.tcl
ot_ci_begin
ot_ci_clock_entry clk 86.424 86.4
set p [[ord::get_db_block] findBTerm clk]
set boxes [[lindex [$p getBPins] 0] getBoxes]
if {[llength $boxes]!=1} {error "clock pin boxes"}
set q [lindex $boxes 0]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set w [expr {[$q xMax]-[$q xMin]}];set h [expr {[$q yMax]-[$q yMin]}]
if {$w!=round(0.048*$u) || $h!=round(0.48*$u)} {error "CLOCK_SHAPE $w $h"}
puts "PV_CORE_CLOCK_PIN_SHAPE PASS width=[expr {$w/double($u)}] height=[expr {$h/double($u)}] centre=86.424,86.4 nativeM5"
