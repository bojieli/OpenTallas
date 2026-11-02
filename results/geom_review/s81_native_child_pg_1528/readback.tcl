read_db /work/run/results/asap7/kl_dsdv_bksel_q_signed_source/base/2_4_floorplan_pdn.odb
check_power_grid -net VDD
check_power_grid -net VSS
puts "PG_TOPOLOGY_CHECK_PASS VDD VSS"
