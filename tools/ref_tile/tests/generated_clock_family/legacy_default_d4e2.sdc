# ---- PL-KIT landed cluster (fixture): 1 landings, multicycle -setup 2 -hold 3
set ot_lp_lands {0}
set ot_lp_miss 0
foreach ot_ln $ot_lp_lands {
  set ot_lf [get_cells -quiet u_lpl_${ot_ln}_w.*]
  set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r.*]
  if {[llength $ot_lf] == 0} { set ot_lf [get_cells -quiet u_lpl_${ot_ln}_w/*] }
  if {[llength $ot_lt] == 0} { set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r/*] }
  if {[llength $ot_lf] == 0 || [llength $ot_lt] == 0} { incr ot_lp_miss; continue }
  set_multicycle_path -setup 2 -from $ot_lf -to $ot_lt
  set_multicycle_path -hold 3 -from $ot_lf -to $ot_lt
}
puts "OT_LP_LAND_SDC [expr {[llength $ot_lp_lands] - $ot_lp_miss}] of [llength $ot_lp_lands] landings constrained"
