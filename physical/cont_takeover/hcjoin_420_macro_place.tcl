# cont-takeover 2026-10-09: hcjoin_420: the three ot_sram_1r1w_256x256_m2_r2c2 macros (172.824 x 41.064) stacked at the
# centre of the 420 x 420 um frame, >= 60 um from every pin edge (fp-lint macro_edge: the auto placer put two macros
# 2.2 um off the S pin face, pi-hcjoin FLOORPLAN_MARGIN), 33.9 um channels between them (> 12 um sliver rule).
place_macro -macro_name {g_sram\[0\].m} -location {169.992 109.89} -orientation R0
place_macro -macro_name {g_sram\[1\].m} -location {169.992 184.95} -orientation R0
place_macro -macro_name {g_sram\[2\].m} -location {169.992 260.01} -orientation R0
