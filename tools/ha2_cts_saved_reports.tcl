# Read-only reporting from the captured CTS failure; no CTS or repair replay.
source $::env(SCRIPTS_DIR)/load.tcl
source_env_var_if_exists PLATFORM_TCL
source $::env(SCRIPTS_DIR)/read_liberty.tcl
read_db /diagnostic/failed_cts.odb
read_sdc /diagnostic/failed_cts.sdc
if {[file exists $::env(PLATFORM_DIR)/derate.tcl]} {source $::env(PLATFORM_DIR)/derate.tcl}
if {[env_var_exists_and_non_empty LAYER_PARASITICS_FILE]} {source $::env(LAYER_PARASITICS_FILE)} else {source $::env(PLATFORM_DIR)/setRC.tcl}
estimate_parasitics -placement
foreach mode {min max} {
  report_checks -path_delay $mode -group_path_count 20 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 6 > /diagnostic/worst_${mode}.rpt
  foreach port {arrival_data arrival_v} {
    set ports [get_ports ${port}*]
    report_checks -from $ports -path_delay $mode -group_path_count 20 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 6 > /diagnostic/${port}_${mode}.rpt
  }
}
report_clock_skew > /diagnostic/clock_skew.rpt
