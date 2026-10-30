read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_db /base/6_final.odb
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]

set src [get_ports cland_tstart_in]
if {[llength $src]!=1} {error "actual cland_tstart_in missing"}
set dst [get_pins -quiet u_cland_origin*/D]
if {[llength $dst]==0} {error "native origin D endpoints missing"}
puts {NATIVE_CASE min rise}
report_checks -rise_from $src -rise_to $dst -path_delay min -unconstrained -format full_clock_expanded -digits 6 -group_path_count 10
puts {NATIVE_CASE min fall}
report_checks -fall_from $src -fall_to $dst -path_delay min -unconstrained -format full_clock_expanded -digits 6 -group_path_count 10
puts {NATIVE_CASE max rise}
report_checks -rise_from $src -rise_to $dst -path_delay max -unconstrained -format full_clock_expanded -digits 6 -group_path_count 10
puts {NATIVE_CASE max fall}
report_checks -fall_from $src -fall_to $dst -path_delay max -unconstrained -format full_clock_expanded -digits 6 -group_path_count 10
puts NATIVE_REPORT_DONE
