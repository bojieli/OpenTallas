# HBM-EP-CAL-1: dump built clock tree (buffer->buffer/sink edges) + per-sink TT arrival (placement RC) for the render.
set P $::env(PLATFORM_DIR)
read_db $::env(ODB)
foreach f [glob $P/lib/NLDM/*_RVT_TT_*] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_tt.lib] { read_liberty $f }
read_sdc $::env(SDC)
source $::env(LAYER_PARASITICS_FILE)
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set fh [open /work/tree_cal1.txt w]
set blk [ord::get_db_block]
set dbu [expr {double([$blk getDefUnits])}]
set todo [list [$blk findNet clk]]
set seen [dict create]
while {[llength $todo]} {
  set n [lindex $todo 0]; set todo [lrange $todo 1 end]
  if {$n eq "NULL" || [dict exists $seen [$n getName]]} continue
  dict set seen [$n getName] 1
  set dx ""; set dy ""
  foreach it [$n getITerms] { if {[$it isOutputSignal]} { set b [[$it getInst] getBBox]; set dx [expr {([$b xMin]+[$b xMax])/2/$dbu}]; set dy [expr {([$b yMin]+[$b yMax])/2/$dbu}] } }
  if {$dx eq ""} { foreach bt [$n getBTerms] { foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] { set dx [expr {([$bx xMin]+[$bx xMax])/2/$dbu}]; set dy [expr {([$bx yMin]+[$bx yMax])/2/$dbu}] } } } }
  foreach it [$n getITerms] {
    if {![$it isInputSignal]} continue
    set inst [$it getInst]; set m [[$inst getMaster] getName]; set b [$inst getBBox]
    set x [expr {([$b xMin]+[$b xMax])/2/$dbu}]; set y [expr {([$b yMin]+[$b yMax])/2/$dbu}]
    if {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m]} {
      puts $fh [format "B %.3f %.3f %.3f %.3f %s" $dx $dy $x $y $m]
      foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
    } else {
      set pn "[$inst getName]/[[$it getMTerm] getName]"
      set a [get_property [get_pins $pn] arrival_max_rise]
      puts $fh [format "S %.3f %.3f %.3f %.3f %s %s" $dx $dy $x $y $a $m]
    }
  }
}
close $fh
puts "OT_CAL1_DUMP nets [dict size $seen]"
# longest TT clock path detail
set worst ""; set wa -1
foreach p [get_pins -hierarchical */CLK] { set a [get_property $p arrival_max_rise]; if {$a ne "" && $a ne "INF" && $a > $wa} { set wa $a; set worst $p } }
puts "OT_CAL1_WORST [get_full_name $worst] $wa"
report_checks -path_delay min_max -to $worst -format full_clock_expanded -fields {slew cap fanout} -digits 1 -group_path_count 1
report_clock_skew
