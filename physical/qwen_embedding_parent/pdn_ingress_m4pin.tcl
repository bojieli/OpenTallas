# Ingress child PDN whose power pins are on M4 (qwen-missing 2026-10-07): the parent embedding banks use
# physical/qwen_slab_m5/pdn_m5.tcl (M1/M2 rails, M5 straps, macro grid M4-M5).  The first child view had its
# VDD/VSS pins on M6 (ORFS default grid), which the parent's M4-M5 macro grid cannot reach (PDN-0233,
# qfd_embed_code_bank_parent-a75c74203).  This grid ends at M4: M1/M2 follow-pin rails, horizontal M4 straps as
# the pins (-pins M4), exactly the pin layer of ot_rom_4096x266_m8, so the parent's M5 straps cross and via down to
# them the way they reach the ROM macros.  The child must be routed on M2-M4 only (route_master RLAYERS='M2 M4') so
# its abstract has no M5 obstruction over the parent's straps.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M4}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M4} -width {0.096} -spacing {0.288} -pitch {2.16} -offset {0.540}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M4}
