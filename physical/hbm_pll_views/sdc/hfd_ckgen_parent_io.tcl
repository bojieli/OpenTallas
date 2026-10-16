# H-DIE-CKGEN 2026-10-16: hfd_ckgen parent boundary (see hfd_ckgen_parent.sdc).  Sourced at the end of the parent SDC and
# after every io_ref / io_plain boundary reset (spec boundary_tcl), so every stage times the same boundary.
#   por_X  setup: arrival(por_X) - arrival(pll_X port) <= 220 ps  (out max = T - 220 - 60 setup uncertainty)
#          hold : arrival(por_X) - arrival(pll_X port) >= -50 ps  (out min = 25 hold uncertainty + 50)
#   pll_*  clock forwards (generated clocks at the port): no data constraint;  por_n: asynchronous assert.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {d per} {stream 833.333 serial 1111.111 hbm 1024 link 833.333} {
  set_output_delay [expr {$per - 220.0 - 60.0}] -max -clock pll_${d}_o [get_ports por_${d}]
  set_output_delay [expr {25.0 + 50.0}] -min -clock pll_${d}_o [get_ports por_${d}]
}
set_false_path -from [get_ports por_n]
