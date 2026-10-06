read_db /retained/results/asap7/opentallas_ot_hbm_integrated_su_cp_context_asap7_harvey_cp_parent_context_r1/base/2_3_floorplan_tapcell.odb
source /out/pdn.tcl
pdngen -failed_via_report /out/failed_vias.rpt
check_power_grid -net VDD
check_power_grid -net VSS
write_db /out/verified_pdn.odb
puts "OT_CP_LOCAL_PDN_PASS"
exit
