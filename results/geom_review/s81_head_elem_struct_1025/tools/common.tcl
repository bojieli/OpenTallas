# HEAD-ELEM probe (read-only): per-sink clock arrival + hold endpoints + w_r[244] slew net, for one parasitic basis
set B $::env(BASE); set MODE $::env(MODE); set OUT $::env(OUT); set C $::env(CORN)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
read_liberty /kit/macros/ot_rom_4096x274_m8_[string tolower $C].lib
if {$MODE eq "rcx"} {
  read_db $B/6_final.odb
  read_spef $B/6_final.spef
} else {
  read_db $B/5_1_grt.odb
  source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
  set_global_routing_layer_adjustment M2-M5 0.5
  set_routing_layers -signal M2-M5 -clock M2-M5
  global_route -congestion_iterations 30 -resistance_aware
  estimate_parasitics -global_routing
}
read_sdc /kit/signoff/ff/sdcdir/golden.sdc
set_propagated_clock [all_clocks]
set vc [get_clocks vclk]
set_input_delay -min -40 -clock $vc [lsearch -all -inline -not [all_inputs] [get_ports clk]]
set_output_delay -min 0 -clock $vc [all_outputs]
set ::ot_ps_lib_only 1; set ::ot_ps_method tag
source /kit/pair_skew.tcl
sta::worst_slack_cmd max; sta::worst_slack_cmd min
set blk [ord::get_db_block]
set fh [open $OUT/ck_${MODE}_${C}.tsv w]
set clk [get_clocks clk]
foreach p [all_registers -clock_pins] {
  set a [ot_ps_ckarr $p $clk min]; set b [ot_ps_ckarr $p $clk max]
  set in [regsub {/[^/]+$} [get_full_name $p] {}]
  set i [$blk findInst $in]
  if {$i eq "NULL"} { set x -1; set y -1 } else { set bb [$i getBBox]; set x [expr {[$bb xMin]/1000.0}]; set y [expr {[$bb yMin]/1000.0}] }
  puts $fh "$in\t$x\t$y\t$a\t$b"
}
close $fh
puts "HEP WNS_MIN [sta::worst_slack_cmd min] WNS_MAX [sta::worst_slack_cmd max] NVIOL_MIN [sta::endpoint_violation_count min] SLEWV [sta::max_slew_violation_count]"
report_checks -path_delay min -group_path_count 400 -endpoint_path_count 1 -slack_max 15 -format end > $OUT/hold_end_${MODE}_${C}.rpt
set fh [open $OUT/hold_pairs_${MODE}_${C}.tsv w]
foreach pe [find_timing_paths -path_delay min -group_path_count 400 -endpoint_path_count 1 -slack_max 15] {
  set pp [[$pe path] pins]; puts $fh "[get_full_name [lindex $pp 0]]\t[get_full_name [$pe pin]]\t[$pe slack]"
}
close $fh
if {[catch {
set d [get_pins {u_m.w_r[244]$_DFF_P_/D}]
report_checks -path_delay max -through $d -format full_clock_expanded -fields {slew cap fanout input_pins} -digits 2 > $OUT/wr244_${MODE}_${C}.rpt
set n [get_nets -of_objects $d]
puts "HEP WR244 net [get_full_name $n] slewD [get_property $d slew_max]"
report_net [get_full_name $n] >> $OUT/wr244_${MODE}_${C}.rpt
# driver chain locations
set fh [open $OUT/wr244_loc_${MODE}_${C}.tsv w]
foreach pe [find_timing_paths -path_delay max -through $d] {
  foreach pa [[$pe path] pins] {
    set pn [get_full_name $pa]; set in [regsub {/[^/]+$} $pn {}]; set i [$blk findInst $in]
    if {$i ne "NULL"} { set bb [$i getBBox]; puts $fh "$pn\t[[$i getMaster] getName]\t[expr {[$bb xMin]/1000.0}]\t[expr {[$bb yMin]/1000.0}]" } else { puts $fh "$pn\tPORT" }
  }
}
close $fh
} err]} { puts "HEP wr244 skipped: $err" }
puts "HEP done"
