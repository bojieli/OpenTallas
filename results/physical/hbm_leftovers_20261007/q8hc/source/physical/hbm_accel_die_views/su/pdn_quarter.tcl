# CLAUDE HBM-ABSTRACTS (hub): PDN of a hub quarter envelope = the view contract (common/pdn_view.tcl: M1/M2 rails,
# M5, M6 straps, M7 stripes 0.288 / 10.8, VDD x 1.0, VSS x 6.4, pins M7) with the hard lanes (r2 lane recipe:
# su/pdn_lane_m6.tcl, PG pins on M6, signals M2-M5) fed by the quarter's M7 stripes through M6-M7 vias.  The quarter
# uses no M8 / M9 (die contract).  r1 (lanes with M7 PG pins, quarter M8 straps) broke the contract and is retired.
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
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
define_pdn_grid -macro -default -name {lanes} -voltage_domains {CORE} -halo {2 2 2 2}
add_pdn_connect -grid {lanes} -layers {M6 M7}
