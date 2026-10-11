# dsfd_engram_c ALL-TILE composition (el1011-ds-misc/engram 2026-10-11), outline 1188 x 432 (die contract: pins N, HBM
# pair W).  The top level holds no register: 8 clocked instances = 2 closed leaves + 6 tiles (each its own clock tree).
# Spec: el1011-ds-misc.log "PHYSICAL SPEC dsfd_engram_c ALL-TILE".  x = 0 mod 0.432, y = 0 mod 2.16.
#   sink  360 x 135      under f_ai (x136-244)                  lkp  324 x 216   N face under T_WIN (aligned pins)
#   T_WIN 327.888 x 47.52 under f_win / t_ag                    T_IO 448.416 x 47.52 under t_vm / f_vm / c_cmd / f_cfg
#   T_WS  388.8 x 120.96  under the sink write port, HBM W pins T_PBB 582.336 x 120.96 bank 1 (bottom band)
#   T_PBC 196.992 x 360.72 bank 0 (u_pb0) / bank 2 (u_pb2) columns, transit R0 E face -> R1 W face (9.5 um, aligned)
place_macro -macro_name {u_sink} -location {40.176 274.32} -orientation R0 -exact
place_macro -macro_name {u_lkp}  -location {410.4 146.88} -orientation R0 -exact
place_macro -macro_name {u_win}  -location {404.784 371.52} -orientation R0 -exact
place_macro -macro_name {u_io}   -location {735.264 371.52} -orientation R0 -exact
place_macro -macro_name {u_ws}   -location {2.592 138.24} -orientation R0 -exact
place_macro -macro_name {u_pb1}  -location {2.592 2.16} -orientation R0 -exact
place_macro -macro_name {u_pb0}  -location {780.192 2.16} -orientation R0 -exact
place_macro -macro_name {u_pb2}  -location {986.688 2.16} -orientation R0 -exact
