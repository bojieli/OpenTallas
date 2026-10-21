# HBM-COLLECT10/COL-HC 10-21 cb rw8 PRE_GLOBAL_PLACE: fence the clk_c stage chain (u_c.cd / u_c.cv) into one box beside the
# d_* (W) / o_* (S) pin groups so the clk_c root is one compact mass (cb_rw6: 127.4 ps over an L around lane leaf g0).
# Released before DPL / CTS by tools/landed_parent/lp_fence_release.tcl (exclusive fences push CTS buffers out).
source /src/physical/ref_tile/hbm_hcq_bank_cb_rw8b/write_pin_names.tcl
set ::lpf_blk [ord::get_db_block]
set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]
set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_chain"]
odb::dbBox_create $::lpf_r [expr {round(10.8*$::lpf_dbu)}] [expr {round(86.4*$::lpf_dbu)}] [expr {round(42.0*$::lpf_dbu)}] [expr {round(178.2*$::lpf_dbu)}]
set ::lpf_g [odb::dbGroup_create $::lpf_r "lp_fence_grp_chain"]
set ::lpf_n 0
foreach i [$::lpf_blk getInsts] {
  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne "CORE"} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} continue
  regsub -all {\\} [$i getName] {} n
  if {![regexp {^u_ot_pr_core\.u_c\.(cd|cv)\[} $n]} continue
  if {[$i getGroup] ne "NULL"} continue
  $::lpf_g addInst $i
  incr ::lpf_n
}
if {$::lpf_n < 200} { error "LP_FENCE chain: only $::lpf_n chain cells matched" }
puts "LP_FENCE chain cells=$::lpf_n box 10.8 86.4 42.0 178.2"
