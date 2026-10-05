# Unchanged baseline PG preflight from d417de733:physical/abi3/check_pg_before_route.tcl.
# Fail before routing if physical power connectivity is broken.
global_connect
check_power_grid -net VDD
check_power_grid -net VSS
puts "OT_MACRO_PG_CHECK_PASS placement physical VDD/VSS connectivity"
