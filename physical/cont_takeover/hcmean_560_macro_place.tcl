# cont-takeover 2026-10-09: hcmean_560: the three ot_sram_1r1w_256x256_m2_r2c2 macros (172.824 x 41.064) stacked at the
# centre of the 560 x 560 um frame, >= 60 um from every pin edge (fp-lint macro_edge: the auto placer put two macros
# 2.2 um off the S pin face, pi-hcjoin FLOORPLAN_MARGIN), 38.9 um channels between them (> 12 um sliver rule).
place_macro -macro_name {g_sram\[0\].u_mem} -location {229.986 170.1} -orientation R0
place_macro -macro_name {g_sram\[1\].u_mem} -location {229.986 250.02} -orientation R0
place_macro -macro_name {g_sram\[2\].u_mem} -location {229.986 329.94} -orientation R0
