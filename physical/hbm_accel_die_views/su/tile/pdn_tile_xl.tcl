# fe-push-hphys-1010 2026-10-10: hfd_su_tile_xl PDN = pdn_quarter.tcl with the lane macro grid halo {W S E N} = {2 0 2 0}.
# The lane's PG pins are on M6 and it fills 162 of the tile's 164.16 um, so the M7 stripes over the lane cross no M6 strap
# inside the tile: with halo 2 on all sides the core straps at y 0.600 (VDD) and 163.176 (VSS), the only ones above /
# below the lane (u_lane at y 0.960 .. 162.960), were cut, and the lane + its M7 stripes were a floating island
# (569572532 hm0/hm10: PSM-0069 VDD, 'Unconnected instance u_lane/VDD', the first su tile route to reach 6_report).
# S / N halo 0 keeps those two straps (0.072 / 0.216 um from the lane edge), so every M7 stripe over the lane lands on them.
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
# hardcore-1010 [tilexl] 2026-10-10: halo {2 0 2 0} alone did NOT fix PSM-0069 (4f0925af4 hm0 + hm10 attempt 1, same
# u_lane/VDD island): with -offset 0.600 the M6 pattern starts VSS (y 1.14) / VDD (y 1.716) from the core edge (y 0.54), so the
# only straps outside the lane's y span (0.96 .. 162.96) are VSS (y 1.14, 163.14); the first VDD strap lies over the lane, is
# trimmed at x 97.75 by the lane's M6 PG pins, and the M7 VDD stripes over the lane reach no VDD M6.  Phase the pattern so a
# VDD strap lands below the lane (y 0.606-0.894) and a VSS strap above it (y 163.182-163.470); VDD pairs with 162.606 at the top,
# VSS with 1.182 at the bottom.  Verified with pdngen + check_power_grid on the 4f0925af4 2_3_floorplan_tapcell.odb: VDD and VSS
# both connected (the 0.600 phase reproduces PSM-0069 / PSM-0039 u_lane/VDD there).  Pitch, widths and the M7 pin contract unchanged.
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.210} -starts_with POWER
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
define_pdn_grid -macro -default -name {lanes} -voltage_domains {CORE} -halo {2 0 2 0}
add_pdn_connect -grid {lanes} -layers {M6 M7}
