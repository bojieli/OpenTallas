
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_verilog /w/mapped.v
link_design ot_qwen_rom_core
create_clock -name clk -period 833.0 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_max_transition 320 [current_design]
set_max_fanout 24 [current_design]
set ::ot_focus [list fsm {(^|\.)(st|state|pc|fpc)(\[|\$)} issue {(^|\.)(fq_n|pend1|nx_v|d_wait_me|d_wait_su|waited|progress|d_chase_n)(\[|\$)} dynp {(^|\.)dynp\[} dyn {(^|\.)dyn\[} decode {(^|\.)(me_nout|me_tiles|me_k|me_wbase|me_xbase|me_obase|su_nin|a_base|b_base|c_base|d_base)\[}]
proc ot_phase {tag} {
  set r2r [find_timing_paths -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay max -group_path_count 1]
  if {[llength $r2r]} { puts "OT_${tag}_R2R_WS [get_property [lindex $r2r 0] slack]" } else { puts "OT_${tag}_R2R_WS NONE" }
  puts "OT_${tag}_ALL_WS [sta::worst_slack_cmd max]"
  puts "OT_${tag}_TNS [sta::total_negative_slack_cmd max]"
  puts "OT_${tag}_CELLS [llength [get_cells *]]"
  puts "OT_${tag}_PATH_BEGIN"
  report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -fields {fanout cap slew} -digits 1
  puts "OT_${tag}_PATH_END"
  foreach {fname fre} $::ot_focus {
    set pins {}
    foreach c [concat [all_registers -cells] [get_cells -quiet -filter "ref_name=~ICG*" *]] { if {[regexp -- $fre [get_full_name $c]]} { foreach pn [get_pins -of_objects $c -filter "direction==input"] { set nm [get_property $pn lib_pin_name]; if {$nm eq "D" || $nm eq "ENA" || $nm eq "SE"} { lappend pins $pn } } } }
    puts "OT_${tag}_FOCUS_N_${fname} [llength $pins]"
    if {[llength $pins]} {
      set fp [find_timing_paths -to $pins -path_delay max -group_path_count 1]
      if {[llength $fp]} { puts "OT_${tag}_FOCUS_WS_${fname} [get_property [lindex $fp 0] slack]" }
      puts "OT_${tag}_FPATH_${fname}_BEGIN"
      report_checks -to $pins -path_delay max -group_path_count 1 -fields {fanout cap slew} -digits 1
      puts "OT_${tag}_FPATH_${fname}_END"
    }
  }
}
puts OT_SKIP_RAW
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
initialize_floorplan -utilization 30 -aspect_ratio 1 -core_space 2 -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
# a block with more ports than its perimeter holds (wide memory ports, exposed black boxes) is placed
# without its I/O (-skip_io): register-to-register paths stay meaningful, I/O paths do not
set nio [expr {[llength [all_inputs]] + [llength [all_outputs]]}]
puts "OT_NIO $nio"
if {$nio <= 4000} {
  global_placement -density 0.6
} else {
  global_placement -density 0.6 -skip_io
}
estimate_parasitics -placement
repair_design -slew_margin 0 -cap_margin 0
detailed_placement
estimate_parasitics -placement
repair_timing -setup -setup_margin 0
detailed_placement
estimate_parasitics -placement
ot_phase REP
exit
