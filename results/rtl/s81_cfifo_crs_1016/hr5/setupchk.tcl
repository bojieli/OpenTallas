set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
set ::ot_ce_corner tt
read_sdc /src/physical/ref_tile/s81coll_cfifo_crs/signoff.sdc
set o [get_pins -quiet {u_x.u_cross.o[*]$_DFF_PN0_/D u_x2.u_cross.o[*]$_DFF_PN0_/D}]
puts "SC o pins [llength $o]"
report_checks -path_delay max -to $o -from [get_clocks ot_entry_1] -format full_clock_expanded -digits 1 -fields {fanout cap slew}
report_checks -path_delay max -to $o -from [get_clocks {ot_entry_2 ot_entry_3}] -format full_clock_expanded -digits 1
report_checks -path_delay max -to [get_pins -quiet {xa[*]$_DFF_P_/D xb[*]$_DFF_P_/D x2[*]$_DFF_P_/D cc[*]$_DFF_P_/D}] -format full_clock_expanded -digits 1
report_checks -path_delay max -format end -group_path_count 5
foreach c {ot_entry_0 ot_entry_1 ot_entry_2 ot_entry_3} { foreach d {ot_entry_0 ot_entry_1 ot_entry_2 ot_entry_3} {
  set p [find_timing_paths -path_delay max -from [get_clocks $c] -to [get_clocks $d] -group_path_count 1]
  if {[llength $p]} { puts "SC setup $c>$d [get_property [lindex $p 0] slack] [get_full_name [get_property [lindex $p 0] startpoint]] -> [get_full_name [get_property [lindex $p 0] endpoint]]" } } }
