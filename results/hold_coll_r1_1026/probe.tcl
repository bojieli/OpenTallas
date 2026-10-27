set corner $::env(PC)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_db /work/run/results/asap7/dp_coll_ftc/base/5_1_grt.odb
if {$corner eq "tt"} { set libs [glob $P/lib/NLDM/*RVT_TT*.lib*] } else { set libs [glob $P/lib/NLDM/*RVT_FF*.lib*] }
foreach l $libs { read_liberty $l }
foreach l [glob -nocomplain $P/lib/NLDM/*SLVT_${corner}*.lib* $P/lib/NLDM/*LVT_${corner}*.lib*] {}
read_sdc /work/constraint.sdc
if {$corner eq "ff"} { set_clock_latency -source 202.5 [get_clocks vclk] }
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
# face flop clock latency: s0 (input face) and last-station (output) flops
set fh [open /out/probe_$corner.txt w]
foreach pin [get_pins -hierarchical {u_ft_*_s*/CLK}] {
  set n [get_full_name $pin]
  if {[catch {set a [get_property $pin arrival_max_rise]}]} continue
  puts $fh "CLK $n $a"
}
# output min arrival at ft out ports
foreach p [get_ports *_o\[*\]] {
  set n [get_full_name $p]
  set a [get_property $p arrival_min_rise]
  set b [get_property $p arrival_min_fall]
  puts $fh "OMIN $n $a $b"
}
foreach p [get_ports *_o\[*\]] {
  puts $fh "OMAX [get_full_name $p] [get_property $p arrival_max_rise] [get_property $p arrival_max_fall]"
}
close $fh
