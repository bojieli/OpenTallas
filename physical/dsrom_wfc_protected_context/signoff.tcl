source $::env(SCRIPTS_DIR)/load.tcl
load_design 6_final.odb 6_final.sdc
set_propagated_clock [all_clocks]
set out $::env(REPORTS_DIR)
foreach c {WC BC} {
  read_spef -corner $c $::env(RESULTS_DIR)/6_final.spef
  report_checks -corner $c -path_delay max -format full_clock_expanded -group_path_count 100 > $out/${c}_setup_raw.rpt
  report_checks -corner $c -path_delay min -format full_clock_expanded -group_path_count 100 > $out/${c}_hold_raw.rpt
  report_check_types -corner $c -max_slew -max_capacitance -max_fanout -violators > $out/${c}_electrical_raw.rpt
  foreach cls {divider controller provider producer capture} {
    switch $cls {
      divider {set pat {*u_common_clock*}}
      controller {set pat {*u_stage*u_ctrl*}}
      provider {set pat {*u_memory*}}
      producer {set pat {*u_cfg* *u_whole*}}
      capture {set pat {*u_c8* *u_core_capture*}}
    }
    set pins [get_pins -quiet -hierarchical $pat]
    puts "CLASS $c $cls endpoints [llength $pins]"
    if {[llength $pins]} {
      report_checks -corner $c -to $pins -path_delay max -format full_clock_expanded -group_path_count 40 > $out/${c}_${cls}_setup_raw.rpt
      report_checks -corner $c -to $pins -path_delay min -format full_clock_expanded -group_path_count 40 > $out/${c}_${cls}_hold_raw.rpt
    }
  }
}
check_setup -verbose > $out/unconstrained_context_raw.rpt
report_clock_properties [all_clocks] > $out/clock_properties_raw.rpt
# External IO is explicitly unbound; positive internal slack is not full closure.
puts "CONTEXT INTERNAL_REAL_R4_PROVIDER_PRODUCER_C8; EXTERNAL_IO_UNBOUND; NO_FULL_PARENT_CLOSURE"

# Owner-authorized ideal-source diagnostic: retain all four clock-pair budgets.
source /src/physical/dsrom_wfc_clock_ip_boundary_20261006/report_body_budget.tcl
puts "WFC_SCOPE IDEAL_EXTERNAL_INPUT_DIAGNOSTIC CONDITIONAL_BODY_ONLY NO_SOURCE_QUALIFICATION NO_HEADLINE"

set coverage_file [open "$out/body_port_inventory_raw.rpt" w]
puts $coverage_file "COND_BODY_DIAGNOSTIC external fault/reset/engine IO UNQUALIFIED; no safe-reset or source qualification"
puts $coverage_file "INPUT_BIT_PORT_COUNT [llength [all_inputs]]"
puts $coverage_file "OUTPUT_BIT_PORT_COUNT [llength [all_outputs]]"
foreach port [all_inputs] {puts $coverage_file "INPUT [get_full_name $port]"}
foreach port [all_outputs] {puts $coverage_file "OUTPUT [get_full_name $port]"}
close $coverage_file
