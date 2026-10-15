# el1011-hbm-attn 2026-10-11 (TOP-DOWN LAYER CONTRACT, child_lint (b)/(c)): SN bank PDN with TWO full-length VDD/VSS
# pairs on M6 (the child's top PG layer, exported as pins), both >= 3 um from the S/N pin faces (pairs at y 3.2-4.06 and
# 7.9-8.76 of 11.88), so the parent's M7 strap vias land in the bank interior, never over the face pin rows
# (hi v5 capacity-0 GRT cells under a via6_7 drop 1 um inside the face).  Signals M2-M5; M7 is the parent's.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {4.7} -offset {3.2}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
