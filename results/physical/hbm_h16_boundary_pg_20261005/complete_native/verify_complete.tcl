read_db /baseline/pdn_finite_selected.odb
source /contract/vss_boundary_stitches.tcl
write_db /output/complete_stitched.odb
check_power_grid -net VDD
check_power_grid -net VSS
puts OT_H16_COMPLETE_BOTH_PG_PASS
exit
