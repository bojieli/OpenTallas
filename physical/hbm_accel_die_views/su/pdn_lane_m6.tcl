# CLAUDE HBM-ABSTRACTS (hub): PDN of a hub lane hardened as a quarter macro, top at M6 (r2 lane recipe).  The lane
# routes signals M2-M5 only (measured: a light lane's GRT used M6 / M7 at 3.8 / 3.6 %), so M6 / M7 over a lane carry
# only its M6 PG straps and stay open for the quarter's own wiring (E/W/N/S die pins reach the port band over the lane
# columns on M6 / M7); the quarter's contract M7 stripes (common/pdn_view.tcl) drop onto these M6 PG pins, so the
# quarter keeps the die contract (no M8 inside the quarter).  M1/M2 rails, M5 straps, M6 straps = the view contract's.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
