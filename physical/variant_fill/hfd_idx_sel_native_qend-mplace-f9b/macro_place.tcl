# FILL-9 2026-10-10 hfd_idx_sel_native_qend: deterministic macro floorplan (root cause of codex_idx_qend_clocksliver_319fcfba8
# PDN-0179 "Unable to repair all channels" at (669.76,0.53)-(675.70,1.09) M2 VSS, and of the aa7127b87 FLOORPLAN_MARGIN
# 7 macro gaps < 12 um): rtl_macro_placer (halo 5) left 10 um side-by-side gaps and put macros on the core edge
# (y 0.576 against core 0.54; gm1.m2 top 844.008 against core 844.02).  Same groups/orientations as the RTLMP result
# (pin affinity kept), but every side-by-side gap is 21.6 um (PDN-repairable, > 12 um sliver rule), stacks keep the
# 0.072 um abutment pitch, and every macro is inset 10.8 um from the core boundary.
# gc = ot_sram_1r1w_1024x256 (174.744 x 70.470), gm = ot_sram_1r1w_256x256 (172.800 x 41.040); core 0 0.54 1399.66 844.02.
# north-west group: gm1 stack, then gc0 / gc1 side by side, gc2 under gc0
place_macro -macro_name {core.gm\[1\].u_m.mac.m\[2\].d256.u} -location {10.8 792.18} -orientation MX
place_macro -macro_name {core.gm\[1\].u_m.mac.m\[1\].d256.u} -location {10.8 751.068} -orientation MX
place_macro -macro_name {core.gm\[1\].u_m.mac.m\[0\].d256.u} -location {10.8 709.956} -orientation MX
place_macro -macro_name {core.gc\[0\].u_m.mac.m\[0\].d1024.u} -location {10.8 627.246} -orientation MX
place_macro -macro_name {core.gc\[1\].u_m.mac.m\[0\].d1024.u} -location {207.144 627.246} -orientation MX
place_macro -macro_name {core.gc\[2\].u_m.mac.m\[0\].d1024.u} -location {10.8 556.716} -orientation R0
# south row: gm0
place_macro -macro_name {core.gm\[0\].u_m.mac.m\[1\].d256.u} -location {494.92 11.34} -orientation MY
place_macro -macro_name {core.gm\[0\].u_m.mac.m\[0\].d256.u} -location {689.32 11.34} -orientation MY
place_macro -macro_name {core.gm\[0\].u_m.mac.m\[2\].d256.u} -location {884.12 11.34} -orientation MY
# east column: gm2 / gm3 stack, gc3 on top
place_macro -macro_name {core.gm\[2\].u_m.mac.m\[2\].d256.u} -location {1216.06 11.34} -orientation MY
place_macro -macro_name {core.gm\[3\].u_m.mac.m\[2\].d256.u} -location {1216.06 52.452} -orientation R180
place_macro -macro_name {core.gm\[2\].u_m.mac.m\[0\].d256.u} -location {1216.06 93.564} -orientation R180
place_macro -macro_name {core.gm\[2\].u_m.mac.m\[1\].d256.u} -location {1216.06 134.676} -orientation R180
place_macro -macro_name {core.gm\[3\].u_m.mac.m\[0\].d256.u} -location {1216.06 175.788} -orientation MY
place_macro -macro_name {core.gm\[3\].u_m.mac.m\[1\].d256.u} -location {1216.06 216.9} -orientation MY
place_macro -macro_name {core.gc\[3\].u_m.mac.m\[0\].d1024.u} -location {1214.116 258.006} -orientation R180
