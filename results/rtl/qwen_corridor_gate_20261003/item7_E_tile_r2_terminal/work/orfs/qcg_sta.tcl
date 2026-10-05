
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(QCG_LIBTAG)_*.lib*]] { read_liberty $f }
read_db $::env(QCG_ODB)
read_sdc $::env(QCG_SDC)
read_spef $::env(QCG_SPEF)
set_propagated_clock [all_clocks]
report_units
puts "QCGSTA setup"; report_worst_slack -max -digits 2
puts "QCGSTA hold";  report_worst_slack -min -digits 2
report_tns -digits 2
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded
set nv 0; set nh 0; set pins [get_pins -hierarchical qs*/D]
foreach p $pins {
  if {[get_property $p slack_max] < 0} { incr nv }
  if {[get_property $p slack_min] < 0} { incr nh }
}
puts "QCGSTA failing_D setup $nv hold $nh of [llength $pins]"
