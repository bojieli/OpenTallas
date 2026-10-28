# QC A0 ONEck parent TRIAL PDN. No PG/IR or timing closure claim.
# Child native M5 pins land onto parent horizontal M6, then vertical M7.
# Added M6 metal fraction 2*.12/8.64=2.778%; nominal width+.072 spacing occupancy4.444%.
# M7 metal fraction 2*.12/4.32=5.556%; nominal occupancy8.889%; real routing/IR remain measured gates.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {.018} -pitch {.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {.018} -pitch {.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {.12} -spacing {.072} -pitch {4.32} -offset {2.064}
add_pdn_stripe -grid {top} -layer {M6} -width {.16} -spacing {.072} -pitch {8.64} -offset {2.064}
add_pdn_stripe -grid {top} -layer {M7} -width {.16} -spacing {.072} -pitch {4.32} -offset {2.064}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
# PG-CORECONN-1 (core_pg_connect): 18 placed macro(s) with M5 PG pins onto the tile M6 straps
define_pdn_grid -macro -name {core_pg_M5} -instances {{^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[0\\\]\.g_single\.g_col\\\[0\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[1\\\]\.g_single\.g_col\\\[0\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[2\\\]\.g_single\.g_col\\\[0\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[3\\\]\.g_single\.g_col\\\[0\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[4\\\]\.g_single\.g_col\\\[0\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[0\\\]\.g_single\.g_col\\\[1\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[1\\\]\.g_single\.g_col\\\[1\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[2\\\]\.g_single\.g_col\\\[1\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[3\\\]\.g_single\.g_col\\\[1\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.g_rom_pipe\.g_rph\.g_rb\\\[4\\\]\.g_single\.g_col\\\[1\\\]\.u_leaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[0\\\]\.g_hd\.u_lh\.u_native_rawleaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[1\\\]\.g_hd\.u_lh\.u_native_rawleaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[2\\\]\.g_hd\.u_lh\.u_native_rawleaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[4\\\]\.g_hd\.u_lh\.u_native_rawleaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[5\\\]\.g_hd\.u_lh\.u_native_rawleaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[3\\\]\.g_hd\.u_lh\.u_native_rawleaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[6\\\]\.g_hd\.u_lh\.u_native_rawleaf$} {^u_g\.u_tile\.u_tile\.u_logic\.u_me\.g_hier\.g_sl\\\[7\\\]\.g_hd\.u_lh\.u_native_rawleaf$}} -voltage_domains {CORE} -halo {0}
add_pdn_connect -grid {core_pg_M5} -layers {M5 M6}
