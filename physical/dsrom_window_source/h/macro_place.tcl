# ot_dsrom_window_source_ctl MARGIN 3 HIER (el1011-ds-misc 2026-10-11), die 620 x 620, core 5..615.
# land8 leaves (140.4 x 43.224, acc inputs on their S face): lanes 0-7 / 8-15 on the S row R0 (input face toward the S
# die pins), lanes 16-23 / 24-31 on the N row MX (H = 43.224 = 0.024 mod 0.048: on-track mirrored pins), each centred
# under its own 300 um of die pins, 20.9 um from the core edge; mirror (82.08 sq) at the centre beside the FSM.
# Grid: x = 0 mod 0.432, y = 0 mod 2.16.
place_macro -macro_name {g_land.g_t\[0\].u_land} -location {89.856 25.920} -orientation R0 -exact
place_macro -macro_name {g_land.g_t\[1\].u_land} -location {389.664 25.920} -orientation R0 -exact
place_macro -macro_name {g_land.g_t\[2\].u_land} -location {89.856 550.800} -orientation MX -exact
place_macro -macro_name {g_land.g_t\[3\].u_land} -location {389.664 550.800} -orientation MX -exact
place_macro -macro_name {g_fsm3.u_mirror} -location {268.704 267.840} -orientation R0 -exact
