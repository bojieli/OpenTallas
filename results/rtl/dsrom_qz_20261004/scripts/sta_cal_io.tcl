# q-element sign-off with the output budget re-derived at the MEASURED insertion (physical/abi3/dsrom_qy_elem_io.sdc
# derivation: the outputs are captured by a sibling q-element whose boundary registers sit behind the same insertion;
# max = 360 ps external - sibling SS insertion, min = - sibling FF insertion).  The sibling insertion is this routed
# block's own free-clock boundary register g_qb.b_go at the corner being checked (the 553.2 / 321.8 ps of R_cap0 were
# fixed in the launcher).  Inputs unchanged.  Everything else as sta_corner.tcl.
set C $::env(CORNER)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz] { read_liberty $L/$f }
read_liberty [lindex [glob $L/asap7sc7p5t_SEQ_RVT_${C}_nldm_*.lib*] 0]
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_[string tolower $C].lib
read_db $::env(ODB)
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF) } else { estimate_parasitics -placement }
set_propagated_clock [all_clocks]
set ref [get_pins {u_e.g_qb.b_go$_DFF_PN0_/CLK}]
set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]
puts "OT_INSERTION $C min $lmin max $lmax"
set outs [all_outputs]
if {$C eq "FF"} {
  set_output_delay -min [expr {-$lmin}] -clock [get_clocks core_clk] $outs
  set kind min
} else {
  set_output_delay -max [expr {360.0 - $lmax}] -clock [get_clocks core_clk] $outs
  set kind max
}
puts "OT_STA corner=$C kind=$kind"
puts "OT_WNS [expr {$kind eq "max" ? [sta::worst_slack -max] : [sta::worst_slack -min]}]"
puts "OT_TNS [expr {$kind eq "max" ? [sta::total_negative_slack -max] : [sta::total_negative_slack -min]}]"
report_checks -path_delay $kind -group_path_count 400000 -endpoint_path_count 1 -format end -slack_max 80 > $::env(OUT).ends
report_checks -path_delay $kind -group_path_count 20 -endpoint_path_count 1 -fields {fanout cap slew} -digits 1 > $::env(OUT).paths
