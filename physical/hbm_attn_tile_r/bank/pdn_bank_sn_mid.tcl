# el1011-hbm-attn v7 (coordinator 07:30: pin-access defect): ONE M6 PG pair at the SN bank's mid-height (core y 4.968..5.832), so the
# rows next to the S / N face pin rows carry no M6 strap and no parent via6_7 drop.  half_v5 hi probe (5_1_grt-failed.odb):
# u_mid c1 d[175..189] (M5, S face y 254.04) sat under the parent M7 VSS strap's via6_7 array on the bank's VSS strap
# 1 um inside the face -> capacity-0 GRT cells (also the mid pair at rel 6.7 for u_mid c2 / u_fc s0c1).  Was: M6 pairs at
# core offset 0.6, pitch 5.4 (two bands, one ~1 um from the S face).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {10.8} -offset {4.968}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
