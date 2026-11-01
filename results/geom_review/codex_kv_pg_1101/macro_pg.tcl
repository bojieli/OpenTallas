# PG-CORECONN-1 (core_pg_connect): 5 placed macro(s) with M4 PG pins onto the tile M5 straps
define_pdn_grid -macro -name {core_pg_M4} -instances {{^u_bound\.u_d2d_kv\.u_core\.u_end\.u_link\.g_bank\\\[0\\\]\.u_store\.g_p288\.u_sram$} {^u_bound\.u_d2d_kv\.u_core\.u_end\.u_link\.g_bank\\\[1\\\]\.u_store\.g_p288\.u_sram$} {^u_bound\.u_d2d_kv\.u_core\.u_end\.u_link\.g_bank\\\[2\\\]\.u_store\.g_p288\.u_sram$} {^u_bound\.u_d2d_kv\.u_core\.u_end\.u_link\.g_bank\\\[3\\\]\.u_store\.g_p288\.u_sram$} {^u_bound\.u_dcal\.u_profile$}} -voltage_domains {CORE} -halo {0}
add_pdn_connect -grid {core_pg_M4} -layers {M4 M5}
# PG-CORECONN-1 (core_pg_connect): 1 placed macro(s) with M6 PG pins onto the tile M7 straps
define_pdn_grid -macro -name {core_pg_M6} -instances {{^u_bound\.u_ucie_rom$}} -voltage_domains {CORE} -halo {0}
add_pdn_connect -grid {core_pg_M6} -layers {M6 M7}
