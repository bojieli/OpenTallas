# el1011-hbm-dmafs 10-12: front_nl2_place420.tcl for the flat ot_hgi_dma_front_xsw (macros under u_core): same two columns of 4
proc ot_inst {n} {
  foreach i [[ord::get_db_block] getInsts] {
    set s [string map {\\ "" / .} [$i getName]]
    if {[string length $s] >= [string length $n] && [string range $s end-[expr {[string length $n]-1}] end] eq $n} { return [$i getName] }
  }
  error "ot_inst: no instance *$n"
}
place_macro -macro_name [ot_inst {.lg[0].u_q}] -location {31.92 94.848} -orientation R0
place_macro -macro_name [ot_inst {.lg[1].u_q}] -location {31.92 157.872} -orientation R0
place_macro -macro_name [ot_inst {.lg[2].u_q}] -location {31.92 220.896} -orientation R0
place_macro -macro_name [ot_inst {.lg[3].u_q}] -location {31.92 283.92} -orientation R0
place_macro -macro_name [ot_inst {.lg[4].u_q}] -location {293.232 94.848} -orientation R0
place_macro -macro_name [ot_inst {.lg[5].u_q}] -location {293.232 157.872} -orientation R0
place_macro -macro_name [ot_inst {.lg[6].u_q}] -location {293.232 220.896} -orientation R0
place_macro -macro_name [ot_inst {.lg[7].u_q}] -location {293.232 283.92} -orientation R0
