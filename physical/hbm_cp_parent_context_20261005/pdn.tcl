add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name cp_service -voltage_domains {CORE} -pins {M8 M9}
add_pdn_stripe -grid cp_service -layer M1 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid cp_service -layer M2 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid cp_service -layer M8 -width 0.48 -spacing 0.903450000 -pitch 2.766900000 -offset 1.383450000
add_pdn_stripe -grid cp_service -layer M9 -width 0.48 -spacing 0.903450000 -pitch 2.766900000 -offset 1.383450000
add_pdn_connect -grid cp_service -layers {M1 M2}
add_pdn_connect -grid cp_service -layers {M2 M8}
add_pdn_connect -grid cp_service -layers {M8 M9}
