# CLAUDE S81-PH selt_c HALF-RATE backstop (SEARCH_PIPE 2, rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv): the two search
# units u_ctl.u_cs / u_ctl.u_fs are clocked by ck gated every other cycle (latch + AND), so every flop inside them
# launches and captures only on gated edges: their internal paths get two ck periods (multicycle setup 2 / hold 1).
# Paths into / out of them stay single cycle.  The verdict log carries OT_SELT_HALF.
set ot_su [get_cells -quiet {u_ctl.u_cs.* u_ctl.u_fs.*}]
if {[llength $ot_su] > 0} {
  set_multicycle_path -setup 2 -from $ot_su -to $ot_su
  set_multicycle_path -hold 1 -from $ot_su -to $ot_su
  puts "OT_SELT_HALF multicycle on [llength $ot_su] search-unit cells"
} else {
  puts "OT_SELT_HALF WARNING no search-unit cells matched (expected only before synthesis)"
}
