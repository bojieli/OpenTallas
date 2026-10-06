# CLAUDE HBM-ABSTRACTS (hub): PDN of a hub quarter envelope = the view contract (common/pdn_view.tcl: M1/M2 rails,
# M5, M6 straps, M7 stripes 0.288 / 10.8, VDD x 1.0, VSS x 6.4) PLUS M8 horizontal straps (0.288 / 10.8) across the
# whole quarter, because the hard lanes (PG pins = their own contract M7 stripes, signals M2-M7) are obstructed on M7
# and can only be reached from M8.  DEFECT against the die contract (die owns M8/M9): the quarter consumes M8 at
# 2 x 0.288 / 10.8 = 5.3 % over its whole outline and exposes PG pins on M7 and M8; the die M8 straps must take
# this pitch/offset over the hub quarters (or the quarter must be fed through M7 only, which hard lanes forbid).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7 M8}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_stripe -grid {top} -layer {M8} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -macro -default -name {lanes} -voltage_domains {CORE} -halo {2 2 2 2}
add_pdn_connect -grid {lanes} -layers {M7 M8}
