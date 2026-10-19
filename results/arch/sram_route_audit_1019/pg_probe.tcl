read_db /base/6_final.odb
check_power_grid -net VDD -floorplanning -error_file /audit/VDD_connectivity.rpt
check_power_grid -net VSS -floorplanning -error_file /audit/VSS_connectivity.rpt
exit
