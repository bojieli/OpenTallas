# half-rate cores (ot_dsrom_su_softmax_exp_hr / ot_dsrom_su_fdiv_hr): every core-internal path runs on a clock-gated
# half-rate domain, so it gets two cycles.  Instances u_a (even cycles) and u_b (odd cycles); hold stays at the normal edge.
foreach inst {u_a u_b} {
  set cells [get_cells -quiet "${inst}.*"]
  if {[llength $cells]} {
    set_multicycle_path -setup 2 -from $cells -to $cells
    set_multicycle_path -hold 1 -from $cells -to $cells
  }
}
