set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_TT*] { read_liberty $f }
read_db $base/4_1_cts.odb
read_sdc $base/4_cts.sdc
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
set ::ot_ce_corner tt
read_sdc /src/physical/ref_tile/hcoll_vmwrite_static_v6_roots_wmid/signoff.sdc
puts "PLACEMENT_DIAGNOSTIC_WS tt max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"
write_timing_model -library_name writer6_wmid_placement_tt /out/ot_hgi_coll_static_vmwrite_roots_v6_physical_tt.lib
puts "PLACEMENT_DIAGNOSTIC_DONE tt"
exit
