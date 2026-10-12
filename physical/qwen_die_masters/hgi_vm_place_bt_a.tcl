# el1011-hbm-hcvm/vm 2026-10-11: ot_hgi_vm_btile variant a: the bank's 5 macros in ONE column on the left face,
# bottom-up VM lo, VM hi (read path next to the bottom-face return pins), then the 3 W2 queue SRAMs (next to the top-face
# lane pins); y channels >= 20.2 um, x 21.6+ um to the core edge; logic (pin flops, select/encode, decode) right of it.
place_macro -macro_name {u_lo} -location {21.600 21.60} -orientation R0
place_macro -macro_name {u_hi} -location {21.600 112.32} -orientation R0
place_macro -macro_name {g_w2\[0\].g_on.u_q} -location {21.600 203.04} -orientation R0
place_macro -macro_name {g_w2\[1\].g_on.u_q} -location {21.600 301.344} -orientation R0
place_macro -macro_name {g_w2\[2\].g_on.u_q} -location {21.600 399.60} -orientation R0
