foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*] { read_liberty $f }
read_liberty /work/macros/ot_rom_4096x266_m8_tt.lib
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
proc rep {tag} {
  foreach p {u_rom/clk u_lg.sel_c$_DFF_PN0_/CLK} {
    set pin [get_pins $p]
    puts "$tag $p rise [sta::format_time [sta::vertex_worst_arrival_path [sta::pin_vertex $pin] max] 2]"
  }
  report_clock_latency -include_internal_latency
  report_checks -path_delay max -to [get_pins {u_lg.sel_c$_DFF_PN0_/RESETN}] -format full -fields {slew cap input} -digits 1
}
estimate_parasitics -placement
puts "=== PLACEMENT RC"
report_clock_skew -digits 1
report_checks -path_delay min -through [get_pins clkbuf_regs_0_clk/A] -format full_clock_expanded -fields {slew cap input} -digits 1 -group_path_count 1
read_spef /base/6_final.spef
puts "=== SPEF"
report_clock_skew -digits 1
report_checks -path_delay min -through [get_pins clkbuf_regs_0_clk/A] -format full_clock_expanded -fields {slew cap input} -digits 1 -group_path_count 1
