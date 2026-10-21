# HBM-COLLECT10/HCE2 10-21 rw7 landing multicycles (LANDING-CONTRACT L5, as tools/landed_parent/lp.py):
# chain ring u_lcw (clk_c) -> read u_lcr (clk_ce): D 4 / K 2 -> -setup 2 -hold 3; f ring u_lfw (clk_w3) -> f_e (clk_x3): D 4 / K 1 -> -hold 3
proc ot_hce2_cells {pat} {
  set c [get_cells -quiet -hierarchical $pat]
  if {[llength $c] == 0} { set c [get_cells -quiet $pat] }
  return $c
}
set ot_hce2_n 0
set ot_lf [ot_hce2_cells *u_lcw.*]; set ot_lt [ot_hce2_cells *u_lcr.*]
if {[llength $ot_lf] && [llength $ot_lt]} { set_multicycle_path -setup 2 -from $ot_lf -to $ot_lt; set_multicycle_path -hold 3 -from $ot_lf -to $ot_lt; incr ot_hce2_n }
set ot_lf [ot_hce2_cells *u_lfw.*]; set ot_lt [ot_hce2_cells *g_spl.f_e*]
if {[llength $ot_lf] && [llength $ot_lt]} { set_multicycle_path -hold 3 -from $ot_lf -to $ot_lt; incr ot_hce2_n }
puts "OT_LP_LAND_SDC $ot_hce2_n of 2 landings constrained (hce2 rw7)"
