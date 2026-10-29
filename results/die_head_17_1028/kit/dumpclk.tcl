read_db /work/run/results/asap7/dp_hd_tile/base/4_1_cts.odb
set b [ord::get_db_block]
set fh [open /work/meas17g/clkcells.txt w]
foreach i [$b getInsts] {
  set n [$i getName]; set r [$i getBBox]
  set x [expr ([$r xMin]+[$r xMax])/2000.0]; set y [expr ([$r yMin]+[$r yMax])/2000.0]
  if {[[$i getMaster] isBlock]} { puts $fh "MAC $n [expr [$r xMin]/1000.0] [expr [$r yMin]/1000.0] [expr [$r xMax]/1000.0] [expr [$r yMax]/1000.0]"; continue }
  if {[string match h16_* $n] || [string match h15_* $n]} { puts $fh "SP $n $x $y [[$i getMaster] getName]"; continue }
  if {[string match clkbuf* $n] || [string match *clkload* $n] || [string match CTS* $n]} { puts $fh "CT $n $x $y"; continue }
}
close $fh
