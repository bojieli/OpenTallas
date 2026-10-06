# Existing W2 parent service context: native local rail bridges, reserved outer M8/M9 PG.
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name w2_service -voltage_domains {CORE} -pins {M8 M9}
add_pdn_stripe -grid w2_service -layer M1 -width 0.018 -pitch 0.54 -offset 0 -followpins
add_pdn_stripe -grid w2_service -layer M2 -width 0.018 -pitch 0.54 -offset 0 -followpins
# Local vertical collectors / horizontal crossbar; explicit M4-M7 via landings.
add_pdn_stripe -grid w2_service -layer M3 -width 0.090 -spacing 2.070 -pitch 4.32 -offset 2.16
add_pdn_stripe -grid w2_service -layer M4 -width 0.120 -spacing 2.040 -pitch 4.32 -offset 2.16
add_pdn_stripe -grid w2_service -layer M7 -width 0.160 -spacing 2.000 -pitch 4.32 -offset 2.16
add_pdn_stripe -grid w2_service -layer M8 -width 0.474 -spacing 2.226 -pitch 5.4 -offset 1.5
add_pdn_stripe -grid w2_service -layer M9 -width 0.474 -spacing 2.226 -pitch 5.4 -offset 1.5
add_pdn_connect -grid w2_service -layers {M1 M2}
add_pdn_connect -grid w2_service -layers {M2 M3}
add_pdn_connect -grid w2_service -layers {M3 M4}
add_pdn_connect -grid w2_service -layers {M4 M7}
add_pdn_connect -grid w2_service -layers {M7 M8}
add_pdn_connect -grid w2_service -layers {M8 M9}
