# DIE-HBM-92-OPEN/Q2NF read-only setup census on kit_periphery_vC 3_place.odb (TT, placement parasitics, ideal clocks)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_TT_nldm_*] { if {![string match *FAKE* $f]} { read_liberty $f } }
foreach f [glob /k/macros/*_tt.lib] { read_liberty $f }
read_db /k/run/results/asap7/hbc_ot_q2nf_rest/base/3_place.odb
read_sdc /k/run/results/asap7/hbc_ot_q2nf_rest/base/3_place.sdc
source /k/setRC_rcx.tcl
estimate_parasitics -placement
report_tns
report_wns
set out [open /o/setup_eps.tsv w]
set n 0
foreach p [find_timing_paths -path_delay max -group_path_count 5000 -endpoint_path_count 1 -slack_max 0] {
  set s [get_property $p slack]
  set sp [get_full_name [get_property $p startpoint]]
  set ep [get_full_name [get_property $p endpoint]]
  puts $out "$s\t$sp\t$ep"
  incr n
}
close $out
puts "OT_CENSUS endpoints_neg $n"
report_checks -path_delay max -group_path_count 6 -format full_clock_expanded -fields {fanout cap slew input_pins} -digits 1 > /o/worst_paths.txt
