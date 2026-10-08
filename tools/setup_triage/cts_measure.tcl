# POST_CTS measurement hook for CTS experiments (tools/setup_triage/cts_exp.sh): sources the block's own POST_CTS hook,
# then reports the clock arrival at every macro / ICG clock pin against the register-sink distribution.
if {[info exists ::env(TRI_ORIG_POST_CTS)] && $::env(TRI_ORIG_POST_CTS) ne ""} { source $::env(TRI_ORIG_POST_CTS) }
estimate_parasitics -placement
set regs {}; set mac {}; set icg {}; set regp {}
foreach p [all_registers -clock_pins] {
  set a [get_property $p arrival_max_rise]
  if {$a eq "" || $a eq "INF"} continue
  set c [get_cells -of_objects $p]
  set r [get_property $c ref_name]
  if {[string match "ot_*" $r] || [string match "*sram*" $r] || [string match "*rom*" $r]} { lappend mac [list [get_full_name $p] $a] } elseif {[string match "ICG*" $r]} { lappend icg [list [get_full_name $p] $a] } else { lappend regs $a; lappend regp [list $a [get_full_name $p]] }
}
foreach c [get_cells -hierarchical -quiet -filter "ref_name=~ICG*"] { set p [get_pins -quiet [get_full_name $c]/CLK]; if {[llength $p]} { lappend icg [list [get_full_name $p] [get_property $p arrival_max_rise]] } }
set regs [lsort -real $regs]; set n [llength $regs]
if {$n} { puts [format "TRI_CTS_REGS n=%d min=%.1f p10=%.1f med=%.1f p90=%.1f max=%.1f" $n [lindex $regs 0] [lindex $regs [expr {$n/10}]] [lindex $regs [expr {$n/2}]] [lindex $regs [expr {$n*9/10}]] [lindex $regs end]] }
set regp [lsort -real -index 0 $regp]
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach e [concat [lrange $regp 0 3] [lrange $regp end-9 end]] {
  set pn [lindex $e 1]; set in [string range $pn 0 [expr {[string last "/" $pn]-1}]]
  set di [$blk findInst $in]; set loc ""; set drv ""
  if {$di ne "NULL" && $di ne ""} {
    lassign [$di getLocation] x y; set loc [format "%.0f,%.0f" [expr {$x/double($dbu)}] [expr {$y/double($dbu)}]]
    set n [[$di findITerm CLK] getNet]
    if {$n ne "NULL"} { set d [$n getFirstOutput]; if {$d ne "NULL" && $d ne ""} { set dd [$d getInst]; lassign [$dd getLocation] dx dy; set drv [format "%s@%.0f,%.0f fo=%d" [$dd getName] [expr {$dx/double($dbu)}] [expr {$dy/double($dbu)}] [llength [$n getITerms]]] } }
  }
  puts [format "TRI_CTS_REGPIN %.1f %s %s drv=%s" [lindex $e 0] $pn $loc $drv]
}
foreach m $mac { puts [format "TRI_CTS_MACRO %s %.1f" [lindex $m 0] [lindex $m 1]] }
foreach m [lsort -unique $icg] { puts [format "TRI_CTS_ICG %s %s" [lindex $m 0] [lindex $m 1]] }
puts "TRI_CTS_WS [sta::worst_slack_cmd max]"
report_checks -path_delay max -group_path_count 3 -endpoint_path_count 1 -format end
