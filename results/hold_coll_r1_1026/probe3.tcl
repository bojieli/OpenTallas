set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_db /work/run/results/asap7/dp_coll_ftc/base/5_1_grt.odb
foreach l [glob $P/lib/NLDM/*RVT_TT*.lib*] { read_liberty $l }
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
set fh [open /out/probe3_tt.txt w]
set blk [ord::get_db_block]
foreach inst [$blk getInsts] {
  set n [$inst getName]
  if {![regexp {^u_ft_.*_s[0-9]+/} $n]} continue
  set it [$inst findITerm CLK]
  if {$it eq "NULL"} continue
  set net [[$it getNet] getName]
  lassign [$inst getLocation] x y
  set pin [get_pins $n/CLK]
  if {[catch {set a [get_property $pin arrival_max_rise]}]} { set a -1 }
  puts $fh "$n $x $y $net $a"
}
close $fh
