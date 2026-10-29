# DIE-QC-36 KITS BTAB QC-014 (B) PRE_GLOBAL_ROUTE: one route from the V1c ROUTED DB (4_cts.odb = V1c 5_2_route.odb), as
# DIE-QC-35 V1d pre_v1d.tcl (kit grt_pre/drv hooks, keep-offs carried by the DB, main clk_freeze: V1c clock wires FIXED,
# every other signal wire ripped) WITHOUT the V1d M4 body region adjustment, PLUS b_strip.tcl (E-strip M5 obstruction +
# M3 corridor reserve).
source /work/grt_pre.tcl
source /work/drv.tcl
set v1d_obs 0
foreach o [[ord::get_db_block] getObstructions] { incr v1d_obs }
puts "B obstructions in routed DB before keep-off hooks: $v1d_obs"
if {$v1d_obs == 0} {
  source /work/sram_pincol_keepoff.tcl
  source /work/sram_edge_m4_keepoff.tcl
}
source /work/clk_freeze.tcl
file mkdir $::env(RESULTS_DIR)/clkdump
ot_clk_dump $::env(RESULTS_DIR)/clkdump/pre_b.txt pre_b
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
puts "B ripped detailed wire of $v1d_rip signal nets; kept FIXED wire of $v1d_keepw clock nets"
source /work/b_strip.tcl
