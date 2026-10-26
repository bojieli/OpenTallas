# el1011-hbm-fq: ot_hgi_dma_front NL=2 (8 lane SRAMs 94.824 x 41.04) fixed placement in a 420 x 420 die (core 10.8..409.2).
# Two columns of 4 (lanes of stacks 0-1 west, 2-3 east), >= 21.1 um to the core edge, 21.98 um channels between macros,
# 166 um logic channel in the centre; all coordinates on the 48 nm grid. Instances resolved by escape-stripped ODB name.
proc ot_inst {n} {
  foreach i [[ord::get_db_block] getInsts] { if {[string map {\\ ""} [$i getName]] eq $n} { return [$i getName] } }
  error "ot_inst: no instance $n"
}
place_macro -macro_name [ot_inst {lg[0].u_q}] -location {31.92 94.848} -orientation R0
place_macro -macro_name [ot_inst {lg[1].u_q}] -location {31.92 157.872} -orientation R0
place_macro -macro_name [ot_inst {lg[2].u_q}] -location {31.92 220.896} -orientation R0
place_macro -macro_name [ot_inst {lg[3].u_q}] -location {31.92 283.92} -orientation R0
place_macro -macro_name [ot_inst {lg[4].u_q}] -location {293.232 94.848} -orientation R0
place_macro -macro_name [ot_inst {lg[5].u_q}] -location {293.232 157.872} -orientation R0
place_macro -macro_name [ot_inst {lg[6].u_q}] -location {293.232 220.896} -orientation R0
place_macro -macro_name [ot_inst {lg[7].u_q}] -location {293.232 283.92} -orientation R0
