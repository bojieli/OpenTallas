# el1011-hbm-attn 2026-10-12 (child_lint (b) spread): SN bank PDN with TWO full-length VDD/VSS pairs on M6 (exported
# as pins) at y 2.176-3.04 and 8.832-9.696 of 11.88 (net-centre spread 6.656 um = 56% >= 50%; the m6x2 pairs at 3.2/7.9 were
# 40%).  Both pairs stay >= 2.18 um off the S/N M5 pin faces (parent M7 via drops in the interior); the M6 clk pin at
# y 5.968 (io_sn*_c6.tcl) sits between the pairs.  Signals M2-M6 around the stripes; M7 is the parent's.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {6.656} -offset {2.176}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
