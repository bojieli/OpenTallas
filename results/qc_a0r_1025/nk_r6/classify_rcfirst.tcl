# PATH-QC-NK 10-25: classify FF hold endpoints of the NK 4_cts.odb (read-only). env PLIBS ODB SDC OUT PLATFORM_DIR
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -placement
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set hard {ot_qwen_tile_romleaf ot_qwen_tile_lsl_fp1 ot_qwen_tile_node}
proc isbuf {i} { set m [[$i getMaster] getName]; return [expr {[string match BUF* $m]||[string match INV* $m]||[string match CKINV* $m]||[string match HB* $m]}] }
# sink inst -> tap port
set tapof [dict create]
foreach bt [$blk getBTerms] {
  set n [$bt getName]
  if {![regexp {^ck(_t[0-9]+)?$} $n]} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  set todo [list $net]; set seen {}
  while {[llength $todo]} {
    set x [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $seen [$x getName]]} continue; dict set seen [$x getName] 1
    foreach it [$x getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]
      if {[isbuf $i]} { foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } } } else { dict set tapof [$i getName] $n }
    }
  }
}
sta::worst_slack_cmd max
sta::worst_slack_cmd min
proc xy {iname} { global blk dbu; set i [$blk findInst $iname]; if {$i eq "NULL"} {return {- -}}; set b [$i getBBox]; return [list [format %.1f [expr {([$b xMin]+[$b xMax])/2.0/$dbu}]] [format %.1f [expr {([$b yMin]+[$b yMax])/2.0/$dbu}]]] }
# hard child clock pins
set fh [open $::env(OUT).cores.tsv w]
puts $fh "inst\tmaster\ttap\tclk_ff_max\tclk_ff_min\tx\ty\tw\th"
foreach i [$blk getInsts] {
  set m [[$i getMaster] getName]
  if {$m ni $hard} continue
  set p [get_pins -quiet "[$i getName]/clk"]
  if {![llength $p]} { set p [get_pins -quiet "[$i getName]/ck"] }
  set a1 [expr {[llength $p] ? [get_property $p arrival_max_rise] : "-"}]
  set a0 [expr {[llength $p] ? [get_property $p arrival_min_rise] : "-"}]
  set t [expr {[dict exists $tapof [$i getName]] ? [dict get $tapof [$i getName]] : "-"}]
  set bb [$i getBBox]
  puts $fh "[$i getName]\t$m\t$t\t$a1\t$a0\t[join [xy [$i getName]] \t]\t[format %.1f [expr {([$bb xMax]-[$bb xMin])/double($dbu)}]]\t[format %.1f [expr {([$bb yMax]-[$bb yMin])/double($dbu)}]]"
}
close $fh
# all clock sinks: inst tap ff arrival (max) x y
set fh [open $::env(OUT).sinks.tsv w]
dict for {iname t} $tapof {
  set ck [get_pins -quiet "$iname/CLK"]; if {![llength $ck]} { set ck [get_pins -quiet "$iname/clk"] }
  set a [expr {[llength $ck] ? [get_property [lindex $ck 0] arrival_max_rise] : "-"}]
  puts $fh "$iname	$t	$a	[join [xy $iname] 	]"
}
close $fh
report_checks -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0.0 -format summary > $::env(OUT).sum
puts "OT_NK_DIAG wns [sta::time_sta_ui [sta::worst_slack_cmd min]] endpoints [sta::endpoint_violation_count min]"
