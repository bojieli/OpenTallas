# Fail before routing if physical power connectivity is broken.
# global_connect only attaches logical PG names; check_power_grid verifies shapes.
global_connect
check_power_grid -net VDD
check_power_grid -net VSS
puts "OT_MACRO_PG_CHECK_PASS placement physical VDD/VSS connectivity"
