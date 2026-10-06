# hfd_attn_tile PDN (CLAUDE HBM-ABSTRACTS attn) P1: the quad's own grid (physical/hbm_attn_tile_r/pdn.tcl: rails
# M1/M2, M5 straps, M8/M9 0.474 um on a 5.4 um pitch, VSS first) with the M8 / M9 offsets chosen so that every strap
# lands on the quads' PG lattice (macro_placement.tcl): M9 VSS centres x = 0.204 mod 5.4, M8 VSS centres
# y = 4.272 mod 5.4 (core origin y 0.54).  The quads' own M9 PG stripes and M8 PG edge stubs then coincide with /
# abut the parent's straps.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M9}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {3.732}
add_pdn_stripe -grid {top} -layer {M9} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {0.204}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M8}
add_pdn_connect -grid {top} -layers {M8 M9}
