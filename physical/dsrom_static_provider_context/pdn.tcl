add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
# Source M2/M5/M6/M7 construction; local origin is the actual sp_capture origin.
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name context -voltage_domains CORE -pins {M7}
add_pdn_stripe -grid context -layer M1 -width 0.018 -pitch 0.540 -offset 0 -followpins
add_pdn_stripe -grid context -layer M2 -width 0.018 -pitch 0.540 -offset 0 -followpins
add_pdn_stripe -grid context -layer M5 -width 0.120 -spacing 0.072 -pitch 2.700 -offset 0.300
add_pdn_stripe -grid context -layer M6 -width 0.288 -spacing 0.096 -pitch 5.400 -offset 0.513
add_pdn_stripe -grid context -layer M7 -width 0.288 -spacing 0.096 -pitch 10.800 -offset 1.000
add_pdn_connect -grid context -layers {M1 M2}
add_pdn_connect -grid context -layers {M2 M5}
add_pdn_connect -grid context -layers {M5 M6}
add_pdn_connect -grid context -layers {M6 M7}
