
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(QA_LIBTAG)_*.lib*]] { read_liberty $f }
read_db $::env(QA_ODB)
read_sdc $::env(QA_SDC)
read_spef $::env(QA_SPEF)
set_propagated_clock [all_clocks]
report_units

foreach p [all_registers -data_pins] {
 set s [get_property $p slack_max]
 if {$s != "INF" && $s < 0} {puts "FAIL_ENDPOINT [get_full_name $p] $s"}
}
report_checks -path_delay max -slack_max 0 -group_path_count 1000 -endpoint_path_count 1 -format full_clock_expanded -digits 4
report_check_types -max_slew -max_fanout -violators -digits 4
