# fe-push t4_join FE variant b: each tap queue macro 40 um in from its own tap pin band (left face, tap t pins y 10+85t..95+85t);
# the tap pin flops (io_flop_at_pins) take the strip between the pins and the macros.  R0: macro pins face east.
place_macro -macro_name {gt\[0\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {40.0 31.98} -orientation R0
place_macro -macro_name {gt\[1\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {40.0 116.98} -orientation R0
place_macro -macro_name {gt\[2\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {40.0 201.98} -orientation R0
place_macro -macro_name {gt\[3\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {40.0 286.98} -orientation R0
