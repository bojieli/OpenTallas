read_db /contract/h16_grid_alignment_test_r2/m4_aligned_copy.odb
check_power_grid -net VDD
check_power_grid -net VSS
puts OT_H16_ALIGNED_PG_BOTH_PASS
