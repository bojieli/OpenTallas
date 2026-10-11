# dsfd_engram_c ALL-TILE composition (el1011-ds-misc/engram 2026-10-11), outline 1188 x 432 (die contract: pins N, HBM
# pair W).  The top level holds no register: 10 clocked instances = 2 closed leaves + 8 tiles (each its own clock tree).
# Spec: el1011-ds-misc.log "PHYSICAL SPEC dsfd_engram_c ALL-TILE".  x = 0 mod 0.432, y = 0 mod 2.16.
#   sink  360 x 135      under f_ai (x136-244)                  lkp  324 x 216   N face under T_WIN (aligned pins)
#   T_WIN 327.888 x 47.52 under f_win / t_ag                    T_IO 448.416 x 38.88 under t_vm / f_vm / c_cmd / f_cfg
#   T_WS  388.8 x 120.96  under the sink write port, HBM W pins bank 1 = pair chain P0 / P1 / P2 233.28 x 120.96 each (bottom band, 4.32 um seams)
#   T_PBC 211.68 x 369.36 bank 0 (u_pb0) / bank 2 (u_pb2) columns, transit R0 E face -> R1 W face (8.64 um, aligned)
place_macro -macro_name {u_sink} -location {40.176 274.32} -orientation R0 -exact
place_macro -macro_name {u_lkp}  -location {410.4 146.88} -orientation R0 -exact
place_macro -macro_name {u_win}  -location {404.784 371.52} -orientation R0 -exact
place_macro -macro_name {u_io}   -location {735.264 380.16} -orientation R0 -exact
place_macro -macro_name {u_ws}   -location {2.592 138.24} -orientation R0 -exact
place_macro -macro_name {u_p0}   -location {2.592 2.16} -orientation R0 -exact
place_macro -macro_name {u_p1}   -location {240.192 2.16} -orientation R0 -exact
place_macro -macro_name {u_p2}   -location {477.792 2.16} -orientation R0 -exact
place_macro -macro_name {u_pb0}  -location {753.84 2.16} -orientation R0 -exact
place_macro -macro_name {u_pb2}  -location {974.16 2.16} -orientation R0 -exact
