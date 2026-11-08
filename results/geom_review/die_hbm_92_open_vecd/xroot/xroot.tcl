read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /k/macros/ot_sram_1r1w_1024x256_m2_r2c2.lef
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {read_liberty $l}
read_liberty /k/macros/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib
read_db /k/run/results/asap7/hbc_hnx_vms_bank_q0_faces__vecd4ae/base/1_synth.odb
read_sdc /k/run/results/asap7/hbc_hnx_vms_bank_q0_faces__vecd4ae/base/1_synth.sdc
set f [open /out/xroot.tsv w]
set n 0
foreach ck [all_registers -clock_pins] {
  set inst [get_cells -of_objects $ck]
  set iname [get_full_name $inst]
  set cnet [get_full_name [get_nets -of_objects $ck]]
  set d [get_pins -quiet $iname/D]
  if {![llength $d]} continue
  set roots {}
  foreach s [get_fanin -to $d -startpoints_only -flat] {
    set sn [get_full_name $s]
    if {[llength [get_ports -quiet $sn]]} {lappend roots PORT:$sn; continue}
    if {[regexp {/(CLK|clk)$} $sn]} {lappend roots [get_full_name [get_nets -of_objects $s]]} else {lappend roots OTHER:$sn}
  }
  puts $f "$iname\t$cnet\t[join [lsort -unique $roots] ,]"
  incr n
}
close $f
puts "XROOT_DONE $n"
