# el1011-hbm-attn v4: bank PDN on M5 only (PG pins M5), so the bank LEF blocks M1-M5 and the parent's M6 (horizontal) runs over every bank; the parent's banks grid straps M6 over the bank and vias M5-M6 (die_tile/pdn_dt_m5b.tcl). half_v3 hi v3nb GRT: 1.04 M of 1.16 M overflow on M6 at 14% M6 use (banks blocked M1-M6, quads M1-M7).
# pipeline bank SN: rails M1/M2, M5 / M6 straps (the core is inset 0.54 um from the S / N edges, so the M5 straps
# stop short of the M5 edge pins), PG pins M6
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M5}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
