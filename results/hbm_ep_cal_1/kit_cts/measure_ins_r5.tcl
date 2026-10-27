# HBM-CORE-LAT-R5: post-CTS clock insertion (clk port -> every register/macro clock pin), placement RC (estimate_parasitics), per corner.
set P $::env(PLATFORM_DIR); set c $::env(OT_CORNER)
read_db $::env(ODB)
foreach f [glob $P/lib/NLDM/*_RVT_${c}_*] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_[string tolower $c].lib] { read_liberty $f }
read_sdc $::env(SDC)
source $::env(LAYER_PARASITICS_FILE)
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set vals {}
foreach p [get_pins -hierarchical */CLK] { set a [get_property $p arrival_max_rise]; if {$a ne "" && $a ne "INF"} { lappend vals $a } }
set m [concat [get_pins -hierarchical -quiet */CK] [get_pins -hierarchical -quiet */clk]]
foreach p $m { set a [get_property $p arrival_max_rise]; if {$a ne "" && $a ne "INF"} { lappend vals $a } }
set n [llength $vals]; set s 0.0; set mn 1e9; set mx -1e9
foreach v $vals { set s [expr {$s + $v}]; if {$v < $mn} {set mn $v}; if {$v > $mx} {set mx $v} }
puts [format "OT_R5_INS corner %s sinks %d mean %.2f min %.2f max %.2f spread %.2f (placement RC, UNCHECKED)" $c $n [expr {$s/$n}] $mn $mx [expr {$mx-$mn}]]
