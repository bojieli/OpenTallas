read_db $::env(ODB)
set b [ord::get_db_block]
set fh [open $::env(OUT) w]
foreach i [$b getInsts] {
  set n [$i getName]
  if {![string match "btcap*" $n]} continue
  set bb [$i getBBox]
  set d [$i findITerm D]; set net [$d getNet]
  set drv "NONE"; set fo 0; set dxy {0 0 0}
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv "[[$it getInst] getName]/[[$it getMTerm] getName]"; set dxy [$it getAvgXY]; set dm [[[$it getInst] getMaster] getName] } else { incr fo } }
  # clock leaf
  set ck [[$i findITerm CLK] getNet]; set leaf ""
  foreach it [$ck getITerms] { if {[$it isOutputSignal]} { set leaf [[$it getInst] getName] } }
  puts $fh "BT $n [expr {[$bb xMin]/1000.0}] [expr {[$bb yMin]/1000.0}] drv $drv $dm [expr {[lindex $dxy 1]/1000.0}] [expr {[lindex $dxy 2]/1000.0}] fo $fo leaf $leaf"
}
close $fh
