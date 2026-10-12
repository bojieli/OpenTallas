# el1011-ds-vm/be 2026-10-11: PDN of the BE v3 parent dsfd_vm_be (1,520.064 x 108) holding 4 hardened dsfd_vm_be_sl tiles.
# Core grid as pdn_view.tcl (rails M1/M2, M5, M6, M7 with the die PG pins on M7) plus an M8 over-macro mesh (pattern of
# physical/dsrom_window_columns/parent_pdn.tcl); the tiles' VDD / VSS pins are M7 stripes (their own pitch-10.8 grid,
# offset by the tile origin), reached from M8 through the macro grid's M7-M8 connect.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -macro -cells {dsfd_vm_be_sl} -halo {2 2 2 2} -voltage_domains {CORE} -name {be_sl}
add_pdn_connect -grid {be_sl} -layers {M7 M8}
