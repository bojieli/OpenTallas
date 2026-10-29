# DIE-QC-35 BTAB QC-014 V1d PRE_GLOBAL_ROUTE (one structural route from the V1c ROUTED DB, 4_cts.odb = V1c 5_2_route.odb):
#  1. the kit's own pre-GRT hooks (grt_pre_core.tcl: vclk binding, drv.tcl, pin-column + pin-face M4/V4 keep-offs);
#     keep-off obstructions already saved in the routed DB are not created twice;
#  2. main clk_freeze: every clock net's V1c detailed wire re-encoded FIXED, clock cells + sinks LOCKED/dont_touch
#     (clock tree, insertion and related pairs stay those of V1c; no clock ECO); dump for clk_geom_diff;
#  3. rip the detailed wire of every other (non-special, non-clock) signal net, so the whole signal route is re-built
#     by GRT + DRT under the new M4 rule (DRC root cause, sram_body_m4_grt_adjust.tcl);
#  4. sram_body_m4_grt_adjust.tcl (M4 region adjustment 1.0 over each macro body + strip).
source /work/grt_pre.tcl
source /work/drv.tcl
set v1d_obs 0
foreach o [[ord::get_db_block] getObstructions] { incr v1d_obs }
puts "V1D obstructions in routed DB before keep-off hooks: $v1d_obs"
if {$v1d_obs == 0} {
  source /work/sram_pincol_keepoff.tcl
  source /work/sram_edge_m4_keepoff.tcl
} else {
  puts "V1D keep-off obstructions carried by the V1c routed DB ($v1d_obs); hooks not re-run"
}
source /work/clk_freeze.tcl
file mkdir $::env(RESULTS_DIR)/clkdump
ot_clk_dump $::env(RESULTS_DIR)/clkdump/pre_v1d.txt pre_v1d
ot_clk_freeze
set v1d_keep [dict create]
foreach n [ot_clk_dbnets] { dict set v1d_keep [$n getName] 1 }
set v1d_rip 0; set v1d_keepw 0
foreach n [[ord::get_db_block] getNets] {
  if {[$n isSpecial] || [$n getSigType] in {POWER GROUND}} continue
  if {[dict exists $v1d_keep [$n getName]]} { incr v1d_keepw; continue }
  set w [$n getWire]
  if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w; incr v1d_rip }
}
puts "V1D ripped detailed wire of $v1d_rip signal nets; kept FIXED wire of $v1d_keepw clock nets"
source /work/sram_body_m4_grt_adjust.tcl
