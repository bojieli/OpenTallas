# Diagnostic only: execute the original image script once, preserve its failure.
set diagnostic_rc [catch {source /diagnostic/original_cts.tcl} diagnostic_message diagnostic_options]
set f [open /diagnostic/cts_status.txt w]
puts $f [list $diagnostic_rc $diagnostic_message]
close $f
write_db /diagnostic/failed_cts.odb
write_sdc /diagnostic/failed_cts.sdc
foreach mode {min max} {
  report_checks -path_delay $mode -group_path_count 20 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 6 > /diagnostic/worst_${mode}.rpt
  foreach port {arrival_data arrival_v} {
    set ports [get_ports ${port}*]
    report_checks -from $ports -path_delay $mode -group_path_count 20 -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 6 > /diagnostic/${port}_${mode}.rpt
  }
}
report_clock_skew > /diagnostic/clock_skew.rpt
if {$diagnostic_rc != 0} {return -options $diagnostic_options $diagnostic_message}
