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
  foreach l {M4 M5} { set_layer_rc -layer $l -resistance 3.0E-02 -capacitance 1.0E-01 }
  puts "HEP RC-CAL M4 M5 R 3.0E-02 C 1.0E-01"
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
set fh [open $OUT/cknodes_${MODE}_${C}.tsv w]
foreach n [get_nets -hierarchical clk*] {
  foreach p [get_pins -quiet -of_objects $n] {
    puts $fh "[get_full_name $p]\t[get_property $p direction]\t[get_property $p arrival_min_rise]\t[get_property $p slew_min_rise]"
  }
}
close $fh
set fh [open $OUT/hold_pairs2_${MODE}_${C}.tsv w]
foreach pe [find_timing_paths -path_delay min -group_path_count 600 -endpoint_path_count 1 -slack_max 15] {
  set pp [[$pe path] pins]; puts $fh "[get_full_name [lindex $pp end]]\t[get_full_name [$pe pin]]\t[$pe slack]"
}
close $fh
set w [lindex [lsort [glob -nocomplain /dev/null]] 0]
report_checks -path_delay min -format full_clock_expanded -digits 2 -fields {slew cap} > $OUT/worst_min_${MODE}_${C}.rpt
puts "HEP done2"
