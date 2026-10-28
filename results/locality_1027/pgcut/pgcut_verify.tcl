read_db /work/run/results/asap7/dp_hd_tile/base/5_1_grt.odb
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
proc wins {} {
  set out {}
  set f [open /out/pgcut_trial.tcl]
  foreach l [split [read $f] "\n"] {
    if {[regexp {^pgc_window ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) +;# (\S+)} $l -> a c d e n]} { lappend out [list $a $c $d $e $n] }
  }
  close $f; return $out
}
proc covered {tag} {
  global b u
  set tot 0
  set fo [open /out/pg_m6_$tag.txt w]
  foreach w [wins] {
    lassign $w a c d e n
    # pin rect = window minus x margin 0.6 (y keeps the 0.072 spacing growth)
    set X0 [expr {round(($a+0.6)*$u)}]; set X1 [expr {round(($d-0.6)*$u)}]
    set Y0 [expr {round($c*$u)}]; set Y1 [expr {round($e*$u)}]
    set k 0
    foreach net {VDD VSS} {
      foreach sw [[$b findNet $net] getSWires] { foreach s [$sw getWires] {
        if {[$s isVia]} continue
        if {[[$s getTechLayer] getName] ne "M6"} continue
        if {[$s xMax] <= $X0 || [$s xMin] >= $X1 || [$s yMax] <= $Y0 || [$s yMin] >= $Y1} continue
        incr k
        if {[string match *rst_n $n] || [string match *clk $n]} { puts "  $tag $n $net M6 [expr {[$s yMin]/double($u)}]-[expr {[$s yMax]/double($u)}]" }
      } }
    }
    # neighbourhood dump for render
    foreach net {VDD VSS} { foreach sw [[$b findNet $net] getSWires] { foreach s [$sw getWires] {
      if {[$s xMax] < $X0-6000 || [$s xMin] > $X1+6000 || [$s yMax] < $Y0-6000 || [$s yMin] > $Y1+6000} continue
      set ln [expr {[$s isVia] ? "VIA" : [[$s getTechLayer] getName]}]
      puts $fo "$n $net $ln [$s xMin] [$s yMin] [$s xMax] [$s yMax]"
    } } }
    puts $fo "PIN $n pin - $X0 [expr {$Y0+72}] $X1 [expr {$Y1-72}]"
    incr tot $k
  }
  close $fo
  puts "OT_VERIFY $tag pins=[llength [wins]] m6_pg_overlaps=$tot"
}
covered before
source /out/pgcut_trial.tcl
covered after
write_db /out/pgcut_5_1_grt.odb
