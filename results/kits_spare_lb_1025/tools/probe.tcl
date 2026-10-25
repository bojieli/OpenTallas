# KITS-SPARE/LB cfg7bfp c2: input-seam hold anatomy (FF) and setup room (TT) on 4_cts.odb, placement RC = setRC_rcx.
set corner $::env(PC)
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set_clock_latency -source $::env(VC) [get_clocks vclk]
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
set ins_nr {}
foreach p [all_inputs] { set n [get_full_name $p]; if {$n ne "rst_n" && $n ne "clk"} { lappend ins_nr $p } }
set regs {}
set fh [open [lindex [glob /work/run/results/asap7/*/base/ot_face_flops.txt] 0] r]
foreach ln [split [read $fh] "\n"] {
  if {$ln eq ""} continue
  set f [split $ln "\t"]; set pn [lindex $f 4]
  set pp [get_ports -quiet $pn]
  if {$pp eq "" || [get_property $pp direction] ne "input" || $pn eq "rst_n"} continue
  dict set regs [lindex $f 0] $pn
}
close $fh
puts "OT_PROBE $corner input_ports [llength $ins_nr] input_pin_regs [dict size $regs]"
if {$corner eq "ff"} { set pd min } else { set pd max }
set fo [open /out/probe_$corner.tsv w]
puts $fo "reg\tport\tin_slack\tin_arr\tck_arr\tq_slack\tq_end"
proc pp {o p} { set v NA; catch { set v [get_property $o $p] }; return $v }
if {$corner eq "ff"} { set sp slack_min } else { set sp slack_max }
foreach r [dict keys $regs] {
  set ck [get_pins -quiet $r/CLK]; set d [get_pins -quiet $r/D]; set q [get_pins -quiet $r/QN]
  if {$q eq ""} { set q [get_pins -quiet $r/Q] }
  if {$ck eq "" || $d eq ""} continue
  puts $fo "$r\t[dict get $regs $r]\t[pp $d $sp]\tNA\t[pp $ck arrival_max_rise]\t[pp $q $sp]\tNA"
}
close $fo
set fo [open /out/out_$corner.tsv w]
foreach p [all_outputs] { puts $fo "[get_full_name $p]\t[pp $p $sp]" }
close $fo
set k 0
foreach r [dict keys $regs] { if {$k < 2} { report_checks -to [get_pins $r/D] -path_delay $pd -fields {slew cap} -digits 1 } ; incr k }
set k 0
foreach p [all_outputs] { if {$k < 1} { report_checks -to $p -path_delay $pd -digits 1 } ; incr k }
puts "OT_PROBE done"
