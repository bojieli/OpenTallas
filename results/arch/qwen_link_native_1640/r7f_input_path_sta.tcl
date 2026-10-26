read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.lef
foreach l {AO_RVT_TT_nldm_211120.lib.gz INVBUF_RVT_TT_nldm_220122.lib.gz OA_RVT_TT_nldm_211120.lib.gz SEQ_RVT_TT_nldm_220123.lib SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_$l }
read_liberty /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_tt.lib
set B $::env(OT_BASE)
read_db $B/6_final.odb
read_sdc $B/6_final.sdc
read_spef $B/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /src/physical/ref_tile/qfd_d2d_static_r7f/signoff.sdc
read_sdc /src/physical/common_flow/io_ref_routed.sdc
puts "=== IO delays"; 
foreach p {rst_n prog_tx_record[78] native_tx_payload[20] x3[390] cfg_data[31] result_tag[26] fdi_rx_flit[3] admit_ready} {
  puts "######## SETUP $p"
  report_checks -path_delay max -from [get_ports $p] -format full_clock_expanded -fields {fanout cap slew input_pin} -digits 1
  puts "######## HOLD $p"
  report_checks -path_delay min -from [get_ports $p] -format full_clock_expanded -fields {fanout input_pin} -digits 1
}
# census: per failing-bus input, number of cells from port to first seq endpoint and their masters
proc chain {p} {
  set net [get_nets -of_objects [get_ports $p]]
  set out {}
  set n 0
  while {$n < 40} {
    set loads [get_pins -of_objects $net -filter "direction==input"]
    if {[llength $loads] != 1} { lappend out "fanout[llength $loads]"; break }
    set inst [get_cells -of_objects $loads]
    set m [get_property $inst ref_name]
    lappend out "[get_property $inst name]:$m"
    if {[string match "*DFF*" $m] || [string match "*SDF*" $m] || [string match "*DHL*" $m]} { break }
    set op [get_pins -of_objects $inst -filter "direction==output"]
    if {[llength $op] != 1} { break }
    set net [get_nets -of_objects $op]
    incr n
  }
  return $out
}
foreach p {rst_n prog_tx_record[78] prog_tx_record[0] native_tx_payload[20] native_tx_payload[300] x3[390] cfg_data[31] fdi_rx_flit[3] fdi_rx_flit[400] result_tag[26] admit_ready} {
  puts "CHAIN $p :: [chain $p]"
}
exit
