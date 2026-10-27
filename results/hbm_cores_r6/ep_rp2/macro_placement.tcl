# HBM-EP-REPACK-1 rp1 (COORD RULING HBM-EP-ROUTE-1 04:04 (b)): SRAM re-pack inside the 250.56x375.84 slot.
# Column x 34.56 (W data edge 30.24 um std-cell column, E 40.39). Stack from the N: upper pair 2.136 apart (pitch 79.92),
# centre band 10.776 (clock entry), lower pair channel 8.616 (pitch 86.4), S std-cell band 30.78 um (4.32 -> 35.10).
# Lattice: every y = 4.86 + 2.16 n  (= row grid 0.27, and y mod 0.048 = 0.012 so the SRAM M4 pin centres (0.012 mod 0.048
# in the macro frame) land on the M4 track grid offset 0.024 pitch 0.048 -> pin access, cf. DRT-0419 on y 17.28).
place_macro -macro_name {u_fcore.u_rxb.g_block\[0\].u_block.g_mem\[1\].u_mem.u_sram} -location {34.56 35.10} -orientation R0 -exact
place_macro -macro_name {u_fcore.u_rxb.g_block\[1\].u_block.g_mem\[1\].u_mem.u_sram} -location {34.56 121.50} -orientation R0 -exact
place_macro -macro_name {u_fcore.u_rxb.g_block\[1\].u_block.g_mem\[0\].u_mem.u_sram} -location {34.56 210.06} -orientation R0 -exact
place_macro -macro_name {u_fcore.u_rxb.g_block\[0\].u_block.g_mem\[0\].u_mem.u_sram} -location {34.56 289.98} -orientation R0 -exact
