source /work/grt_pre_core.tcl
source /work/clk_freeze.tcl
ot_clk_freeze
# Predecessor detailed data wiring is invalid after structural placement. Keep every clock wire and PG special wire.
set clocks [dict create]
foreach n [ot_clk_dbnets] {dict set clocks [$n getName] 1}
set nr 0
foreach n [[ord::get_db_block] getNets] {
 if {[dict exists $clocks [$n getName]] || [$n getSigType] in {POWER GROUND}} continue
 set w [$n getWire]
 if {$w ne "NULL" && $w ne ""} {odb::dbWire_destroy $w;incr nr}
}
set_dont_use [get_lib_cells -quiet */DFF*]
puts "Q1A_FRESH removed $nr stale signal wires; [dict size $clocks] clock routes untouched; all FF resize families disabled"
