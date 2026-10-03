foreach inst [[ord::get_db_block] getInsts] {$inst setDoNotTouch false}
add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power
add_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground
global_connect
foreach inst [[ord::get_db_block] getInsts] {$inst setDoNotTouch true}
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name native_relay -voltage_domains CORE
add_pdn_stripe -grid native_relay -layer M1 -width 0.018 -followpins
add_pdn_stripe -grid native_relay -layer M3 -width 0.090 -pitch 5.616 -spacing 2.718 -offset 0.54 -extend_to_boundary -allow_out_of_core
add_pdn_connect -grid native_relay -layers {M1 M3}
