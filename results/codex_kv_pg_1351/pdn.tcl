add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE}
add_pdn_stripe -grid {top} -layer M8 -width 0.48 -pitch 4.32 -offset 1.080000 -spacing 1.68 -starts_with POWER
add_pdn_stripe -grid {top} -layer M9 -width 12.96 -pitch 39.96 -offset 13.770000 -spacing 7.02 -starts_with POWER
add_pdn_connect -grid {top} -layers {M8 M9}
define_pdn_grid -name {parts} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {0 0 0 0} -default
add_pdn_connect -grid {parts} -layers {M7 M8}
