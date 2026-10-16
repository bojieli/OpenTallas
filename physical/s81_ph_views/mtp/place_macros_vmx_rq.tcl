# mtp-lead 2026-10-11 dsfd_wfc_vmx (345.6 x 324.0; signal pins W 46-317 / E 46-317 / N + S short groups): the RQ 64 x 1032
# read-response queue (RD2) in 5 x ot_sram_1r1w_128x256_m1_r2c2 (94.824 x 41.064, ot_fifo_sram_fwft MACRO 2) in ONE
# centred interior column: x 124.2 (124 um W channel / 126 um E channel for the pin flops and the CDC FIFOs), rows
# y = 32.4 + 54.0 k (12.9 um gaps >= the 12 um sliver limit; 32.4 um S / 34.5 um N channels to the N / S pin groups).
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {u_rq\.g_tile\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_t]} { continue }
  place_macro -macro_name $ot_nm -location [list 124.2 [expr {32.4 + 54.0 * $ot_t}]] -orientation R0
  incr ot_n
}
if {$ot_n != 5} { error "place_macros_vmx_rq: placed $ot_n macros (expected 5)" }
puts "place_macros_vmx_rq: $ot_n macros placed"
