# DIE-QC-50/gen47ndr stage 4: both-edge arrival readout of every clock cell and native tap on the DRT-routed clock with
# the OpenRCX SPEF (rcx.tcl).  Readout block identical to stage 1 grt_ndr.tcl / predecessor grt_src.tcl (DIE-QC-45
# edge_readout format); only the parasitics differ (read_spef instead of estimate_parasitics -global_routing).
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set O $::env(OUT)
set C $::env(CORNER)
set R $::env(RUN)
foreach f [glob $P/lib/NLDM/*RVT_${C}_nldm*.lib*] { read_liberty $f }
read_db $R/drt_$::env(TAG)/clk_drt.odb
set b [ord::get_db_block]
create_clock -name dck -period 833.000 [get_ports root]
set_propagated_clock [all_clocks]
read_spef $R/rcx_$::env(TAG)/clk_rcx.spef
report_parasitic_annotation
set fh [open $O/edges_raw.txt w]
set n 0
foreach inst [$b getInsts] {
  set nm [$inst getName]
  if {[string range $nm 0 2] ne "ck_"} continue
  set p [get_pins -quiet $nm/Y]
  if {![llength $p]} { puts $fh "C $nm [[$inst getMaster] getName] NA"; continue }
  puts $fh "C $nm [[$inst getMaster] getName] [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_rise] [get_property $p slew_max_fall]"
  incr n
}
puts "RD_CELLS $n"
set tf [open $R/taps.txt]
while {[gets $tf l] >= 0} {
  lassign $l t inst pin x y
  set p [get_pins -quiet $inst/$pin]
  if {[llength $p]} {
    set drv ""
    set net [get_nets -quiet -of_objects $p]
    if {[llength $net]} { foreach dp [get_pins -quiet -of_objects $net -filter "direction==output"] { set drv [get_full_name $dp] } }
    puts $fh "T $t [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_rise] $drv"
  } else { puts $fh "T $t NA" }
}
close $tf
close $fh
puts RD_ARR_DONE
