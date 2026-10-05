read_db /work/pdn_finite_selected.odb
foreach net {VDD VSS} {
 puts "CHECK_SELECTED_POWER_GRID $net"
 check_power_grid -net $net
}
puts "PASS_SELECTED_POWER_CONNECTIVITY"
