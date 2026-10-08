# H16 quad parent (ot_attn_tile_m6h1p): the tile grid without the leaf macro grid; the quads sit on its M9 lattice and
# physical/hbm_attn_tile_r/quad_m9_bridge.tcl (POST_PDN) joins their M9 pins to the straps.
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
