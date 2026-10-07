# CLAUDE S81-PH selt_c PING-PONG backstop (SEARCH_PIPE 3, ot_s81ph_sel_ctl_pp.sv): each search unit copy u_a / u_b is
# clocked on alternate gated edges: its internal paths get two ck periods (multicycle setup 2 / hold 1).  The copy
# select flops / muxes (u_cs.last_a, en_q) stay single cycle.
foreach ot_c {u_ctl.u_cs.u_a u_ctl.u_cs.u_b u_ctl.u_fs.u_a u_ctl.u_fs.u_b} {
  set ot_su [get_cells -quiet "$ot_c.*"]
  if {[llength $ot_su] > 0} {
    set_multicycle_path -setup 2 -from $ot_su -to $ot_su
    set_multicycle_path -hold 1 -from $ot_su -to $ot_su
    puts "OT_SELT_PP multicycle on [llength $ot_su] cells of $ot_c"
  }
}
