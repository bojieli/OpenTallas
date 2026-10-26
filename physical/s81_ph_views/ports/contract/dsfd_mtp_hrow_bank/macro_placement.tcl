# dsfd_mtp_hrow_bank (hrow rev 3): 2 x 2 macros around a 72 um register channel (x 194.88 .. 266.88); left column MY (pins
# on its right edge), right column R0 (pins on its left edge); 48 nm grid origins; core margins W 20.16 / E 20.64 /
# S 20.16 / N 21.72 um; row channel 20.18 um.  outline 462.24 x 203.04
place_macro -macro_name {g_c\[0\].u_m} -location {20.16 20.16} -orientation MY -exact
place_macro -macro_name {g_c\[1\].u_m} -location {266.88 20.16} -orientation R0 -exact
place_macro -macro_name {g_c\[2\].u_m} -location {20.16 110.832} -orientation MY -exact
place_macro -macro_name {g_c\[3\].u_m} -location {266.88 110.832} -orientation R0 -exact
