# FILL-9 t4_join MEM=1: each tap queue macro beside its own tap pin band (left face, tap t pins y 10+85t..95+85t, centroid 52.5+85t
# measured in the f9a cal fp-lint dump); RTLMP had put gt[2] 108 um from its pins (bank_distance). R0: macro pins face east, toward the join logic.
place_macro -macro_name {gt\[0\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {12.96 31.98} -orientation R0
place_macro -macro_name {gt\[1\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {12.96 116.98} -orientation R0
place_macro -macro_name {gt\[2\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {12.96 201.98} -orientation R0
place_macro -macro_name {gt\[3\].sr.queue.g_tile\[0\].genblk1.g_m2.u_m} -location {12.96 286.98} -orientation R0
