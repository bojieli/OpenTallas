# Full WINDOW hierarchical upper-metal context: actual leaf VDD/VSS pins are on M6.
# Standard-cell rails reach M8 through M5; real macro pins reach M9 through M6.  Overmacro mesh uses the
# existing 0.1756 M8/M9 PG reservation: 2*0.474/5.4 = 0.1755556.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M9}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_stripe -grid {top} -layer {M9} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M8}
add_pdn_connect -grid {top} -layers {M8 M9}
define_pdn_grid -macro -cells {ot_dsrom_window_column_128 ot_dsrom_window_column_256} -halo {2.05 2.16 2.05 2.15} -voltage_domains {CORE} -name {window_columns}
add_pdn_connect -grid {window_columns} -layers {M6 M9}
