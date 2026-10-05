# Power grid of the reduced-scale V4.1 physical die (rtl/chip/ot_chip_v41x_pdie.sv,
# tools/v41x_die_pnr.py die_s4).  Die-level cells live in the spine, the PHY strips and
# the channels between tiles: M1/M2 rails, M5/M6 stripes there (cut where a macro obstructs
# them), and an M8/M9 mesh over everything as the die grid.  The tile abstracts obstruct
# M1-M7 and bring their own grid (not modelled); the PHY and link placeholders expose power
# on M4 and take M4-M5 vias through their macro grid.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}

define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M9}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {10.8} -offset {1.5}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0}
add_pdn_stripe -grid {top} -layer {M8} -width {0.64} -spacing {0.32} -pitch {40.0} -offset {5.0}
add_pdn_stripe -grid {top} -layer {M9} -width {0.64} -spacing {0.32} -pitch {40.0} -offset {5.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M8}
add_pdn_connect -grid {top} -layers {M8 M9}

source $::env(SCRIPTS_DIR)/util.tcl
set m4 {}
foreach inst [find_macros] {
  set master [[$inst getMaster] getName]
  # tiles (the placeholders and the routed ot_chip_v41x_ptile abstract) bring their own grid (not modelled)
  if {![string match "ot_pdie_tile_*" $master] && $master ne "ot_chip_v41x_ptile"} { dict set m4 $master 1 }
}
if {[llength [dict keys $m4]] > 0} {
  define_pdn_grid -macro -cells [dict keys $m4] -halo {2 2 2 2} -voltage_domains {CORE} -name {m4macros}
  add_pdn_connect -grid {m4macros} -layers {M4 M5}
}
