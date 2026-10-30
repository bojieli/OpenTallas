foreach l $::env(PLIBS) { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [get_clocks clk]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
puts $f "#pin arr_ps x_um y_um depth leaf_inst leaf_master leaf_x leaf_y leaf_arr path_masters"
foreach pin [get_pins -hierarchical */CLK] {
  set n [get_full_name $pin]
  set a [get_property $pin arrival_max_rise]
  set inst [sta::sta_to_db_inst [$pin instance]]
  set loc [$inst getLocation]
  set it [$inst findITerm CLK]
  set depth 0; set masters {}; set leaf ""; set lm ""; set lx 0; set ly 0; set la 0
  set net [$it getNet]
  set guard 0
  while {$net ne "NULL" && $guard < 40} {
    incr guard
    set drv ""
    foreach d [$net getITerms] { if {[$d isOutputSignal]} { set drv $d; break } }
    if {$drv eq ""} { break }
    set di [$drv getInst]
    incr depth
    lappend masters [[$di getMaster] getName]
    if {$leaf eq ""} {
      set leaf [$di getName]; set lm [[$di getMaster] getName]
      set ll [$di getLocation]; set lx [expr {[lindex $ll 0]/double($dbu)}]; set ly [expr {[lindex $ll 1]/double($dbu)}]
      set op [get_pins -of_objects [get_cells [$di getName]] -filter "direction==output"]
      set la [get_property $op arrival_max_rise]
    }
    set net "NULL"
    foreach t [$di getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { set net [$t getNet]; break } }
  }
  puts $f "$n $a [expr {[lindex $loc 0]/double($dbu)}] [expr {[lindex $loc 1]/double($dbu)}] $depth $leaf $lm $lx $ly $la [join $masters ,]"
}
close $f
puts DUMP_DONE
