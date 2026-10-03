add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name native_relay -voltage_domains CORE
add_pdn_stripe -grid native_relay -layer M1 -width 0.018 -followpins
add_pdn_stripe -grid native_relay -layer M3 -width 0.054 -pitch 5.4 -spacing 2.7 -offset 0.54
add_pdn_connect -grid native_relay -layers {M1 M3}
