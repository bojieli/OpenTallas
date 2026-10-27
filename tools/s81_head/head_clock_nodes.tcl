# Read-only after the normal meas_ck.tcl load/RC preamble. GRT-RC clock leg delays.
source /work/mscts_spec_eq.tcl
# get_property arrival accesses graph vertices; force graph construction first.
report_worst_slack -max
set f [open $::env(OUT) w]
puts $f "node\tparent\tnet\tparent_y\tinput_a\toutput_y\tnet_delay\tcell_delay"
foreach row $ot_ms_tree {
  lassign $row n par x y cell
  set pi [expr {$par eq "root" ? "u_isl_root" : "ot_ms_${par}_nd"}]
  set ci ot_ms_${n}_nd
  set nn [expr {$par eq "root" ? "clk" : "ot_ms_${par}_n"}]
  foreach pn [list $pi/Y $ci/A $ci/Y] {
    if {[llength [get_pins $pn]] != 1} { error "Missing planned clock pin $pn" }
  }
  set pa [get_property [get_pins $pi/Y] arrival_max_rise]
  set ia [get_property [get_pins $ci/A] arrival_max_rise]
  set oa [get_property [get_pins $ci/Y] arrival_max_rise]
  puts $f "$n\t$par\t$nn\t$pa\t$ia\t$oa\t[expr {$ia-$pa}]\t[expr {$oa-$ia}]"
}
close $f
foreach n {N0_0 N0_1 N0_2 N0_3 N1_0 N1_1 N1_2 N1_3} {
  puts "CLOCK_NET $n"
  report_net ot_ms_${n}_n
}
exit
