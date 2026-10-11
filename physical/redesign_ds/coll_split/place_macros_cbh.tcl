# el1011-ds-coll: child placement of the cb parent (tools/s81_ph/s81_ph_coll_cbh_parent.py)
set ot_n 0
place_macro -macro_name {u_rw} -location {10.8000 21.6000} -orientation R0; incr ot_n
place_macro -macro_name {u_f} -location {129.6000 21.6000} -orientation R0; incr ot_n
place_macro -macro_name {u_q0} -location {200.0160 21.6000} -orientation R0; incr ot_n
place_macro -macro_name {g_q[1].u_q} -location {283.3920 21.6000} -orientation R0; incr ot_n
place_macro -macro_name {g_q[2].u_q} -location {366.7680 21.6000} -orientation R0; incr ot_n
place_macro -macro_name {g_q[3].u_q} -location {450.1440 21.6000} -orientation R0; incr ot_n
place_macro -macro_name {g_q[4].u_q} -location {533.5200 21.6000} -orientation R0; incr ot_n
place_macro -macro_name {u_re} -location {616.8960 21.6000} -orientation MY; incr ot_n
puts "place_macros_cbh: $ot_n children placed"
