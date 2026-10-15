# dsfd_engram_c HIER (el1011-ds-misc 2026-10-11), outline 1188 x 432, die pins N (W: HBM pair).
# Leaves: sink R0 under the f_ai pins (its write port faces S onto the bank-1 columns), lookup R0 top-centre
# (window / all-gather edge N by f_win / t_ag, HBM edge S -> relayed to the W pins).
# SRAMs placed BY BANK (each bank's 6:1 group select local to one column): bank 0 = column x 836.8 (6 high, by the
# t_vm pins), bank 1 = columns x 45.4 / 243.2 (under the sink write port), bank 2 (64 b) = the bottom of x 243..812.
# Every macro's access pins face W into a 25 um register channel; rows 20 um apart; >= 20 um to the leaves / edges.
# Grid: x = 0 mod 0.432, y = 0 mod 2.16 (M4 / M5 pin tracks of every macro and leaf stay on grid).
place_macro -macro_name {u_sink} -location {40.176 274.32} -orientation R0 -exact
place_macro -macro_name {u_lkp} -location {430.272 194.4} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[0\].g_grp\[0\].u_sram} -location {836.784 19.440} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[0\].g_grp\[1\].u_sram} -location {836.784 82.080} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[0\].g_grp\[2\].u_sram} -location {836.784 144.720} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[0\].g_grp\[3\].u_sram} -location {836.784 207.360} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[0\].g_grp\[4\].u_sram} -location {836.784 270.000} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[0\].g_grp\[5\].u_sram} -location {836.784 332.640} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[1\].g_grp\[0\].u_sram} -location {45.360 19.440} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[1\].g_grp\[1\].u_sram} -location {45.360 82.080} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[1\].g_grp\[2\].u_sram} -location {45.360 144.720} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[1\].g_grp\[3\].u_sram} -location {45.360 207.360} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[1\].g_grp\[4\].u_sram} -location {243.216 19.440} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[1\].g_grp\[5\].u_sram} -location {243.216 82.080} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[2\].g_grp\[0\].u_sram} -location {243.216 144.720} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[2\].g_grp\[1\].u_sram} -location {243.216 207.360} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[2\].g_grp\[2\].u_sram} -location {441.072 19.440} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[2\].g_grp\[3\].u_sram} -location {441.072 82.080} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[2\].g_grp\[4\].u_sram} -location {638.928 19.440} -orientation R0 -exact
place_macro -macro_name {u_pf.g_bank\[2\].g_grp\[5\].u_sram} -location {638.928 82.080} -orientation R0 -exact
