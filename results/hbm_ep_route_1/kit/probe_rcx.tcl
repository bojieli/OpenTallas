# HBM-EP-ROUTE-1: routed (6_final.odb) + RCX SPEF clock insertion per corner, and the S-island trunks over the SRAM column.
set P $::env(PLATFORM_DIR); set c $::env(OT_CORNER)
read_db $::env(ODB)
foreach f [glob $P/lib/NLDM/*_RVT_${c}_*] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_[string tolower $c].lib] { read_liberty $f }
read_sdc $::env(SDC)
read_spef $::env(SPEF)
set_propagated_clock [all_clocks]
set vals {}
foreach p [concat [get_pins -hierarchical */CLK] [get_pins -hierarchical -quiet */clk]] { set a [get_property $p arrival_max_rise]; if {$a ne "" && $a ne "INF"} { lappend vals $a } }
set n [llength $vals]; set s 0.0; set mn 1e9; set mx -1e9
foreach v $vals { set s [expr {$s + $v}]; if {$v < $mn} {set mn $v}; if {$v > $mx} {set mx $v} }
puts [format "OT_RCX_INS corner %s sinks %d mean %.2f min %.2f max %.2f spread %.2f (routed, RCX SPEF)" $c $n [expr {$s/$n}] $mn $mx [expr {$mx-$mn}]]
foreach e {ot_ms_entry1 ot_ms_entry4 ot_ms_root} { set p [get_pins $e/A]; puts [format "OT_RCX_NODE %s %s A arrival %.2f" $c $e [get_property $p arrival_max_rise]] }
set blk [ord::get_db_block]
foreach {tr drv ld} {S_W ot_ms_T00_br_nd ot_ms_T00_r0_nd S_E ot_ms_T10_br_nd ot_ms_T10_r0_nd N_W ot_ms_T01_br_nd ot_ms_T01_r0_nd N_E ot_ms_T11_br_nd ot_ms_T11_r0_nd} {
  set net [[[$blk findInst $ld] findITerm A] getNet]
  set w [$net getWire]; set L [expr {$w eq "NULL" ? -1 : [$w getLength] / 1000.0}]
  set lays {}; if {$w ne "NULL"} { foreach sw [$net getSWires] {}; }
  set pi [get_pins $ld/A]; set po [get_pins $drv/Y]
  puts [format "OT_RCX_TRUNK %s %s net %s routed_len_um %.1f drv_slew %.2f load_slew %.2f arr_drv_in %.2f arr_load_in %.2f stage_ps %.2f" $c $tr [$net getName] $L \
    [get_property $po slew_max] [get_property $pi slew_max] [get_property [get_pins $drv/A] arrival_max_rise] [get_property $pi arrival_max_rise] \
    [expr {[get_property $pi arrival_max_rise] - [get_property [get_pins $drv/A] arrival_max_rise]}]]
}
set wl 0.0; set worst 0.0; set wn ""
foreach net [$blk getNets] { if {[$net getSigType] ne "CLOCK"} continue; set w [$net getWire]; if {$w ne "NULL"} { set wl [expr {$wl + [$w getLength]/1000.0}] } }
foreach p [get_pins -hierarchical ot_ms_*/A] { set sl [get_property $p slew_max]; if {$sl > $worst} { set worst $sl; set wn [get_full_name $p] } }
puts [format "OT_RCX_CLOCKNET %s total_clock_wire_um %.0f worst_tree_input_slew %.2f at %s" $c $wl $worst $wn]
