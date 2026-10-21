# HBM-COLLECT10/HCE2 10-21 rw7 landing multicycles (LANDING-CONTRACT L5, as tools/landed_parent/lp.py):
# chain ring u_lcw (clk_c) -> read u_lcr (clk_ce): D 4 / K 2 -> -setup 2 -hold 3; f ring u_lfw (clk_w3) -> f_e (clk_x3): D 4 / K 1 -> -hold 3
# The chunk selectors are keep_hierarchy instances, so flops are matched on the full name ('.' flattened or '/' kept).
proc ot_hce2_flops {re} {
  set out {}
  foreach c [get_cells -quiet -hierarchical *] {
    if {[regexp $re [get_full_name $c]] && [string match -nocase *DFF* [get_property $c ref_name]]} { lappend out $c }
  }
  return $out
}
set ot_hce2_n 0
set ot_lf [ot_hce2_flops {u_lcw[^A-Za-z0-9_]}]; set ot_lt [ot_hce2_flops {u_lcr[^A-Za-z0-9_]}]
if {[llength $ot_lf] && [llength $ot_lt]} { set_multicycle_path -setup 2 -from $ot_lf -to $ot_lt; set_multicycle_path -hold 3 -from $ot_lf -to $ot_lt; incr ot_hce2_n }
set ot_lf2 [ot_hce2_flops {u_lfw[^A-Za-z0-9_]}]; set ot_lt2 [ot_hce2_flops {g_spl[./]f_e}]
if {[llength $ot_lf2] && [llength $ot_lt2]} { set_multicycle_path -hold 3 -from $ot_lf2 -to $ot_lt2; incr ot_hce2_n }
puts "OT_LP_LAND_SDC $ot_hce2_n of 2 landings constrained (hce2 rw7: [llength $ot_lf]/[llength $ot_lt] chain, [llength $ot_lf2]/[llength $ot_lt2] f flops)"
