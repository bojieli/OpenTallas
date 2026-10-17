# Q-ROMLEAF-FF (2026-10-16): confine the ROM leaf's capture / expansion pipeline to one compact field beside the pin face.
#
# Measured on the closed a0 route (ot_qwen_tile_romleaf-a0-4fe0c00bd, FF hold +7.36): the macro's rd_out[128..255]
# leave on its EAST edge, 122 um from the W pin face, and the placer strung the zero-logic shift stages
# (cap2x -> g -> r_q) along the channel under the macro: g[368] sat 66 um from its pin flop r_q[368], on an early
# H-tree branch (FF clock 141.9 ps) while the pin column is late (169.1 ps); hold was met at GRT only by the
# over-estimated wire RC of that 66 um net (GRT +30.7 -> routed +7.36).  The sink field (W column + under-macro channel +
# an east island of 128 cap flops) is 150 x 65 um, and the H-tree over it spreads 139..195 ps (FF).
#
# Fix: every pipeline register (groups named by OT_RLF_GROUPS) is placed inside the field OT_RLF_BOXES (x0 y0 x1 y1 um,
# one or more boxes, INCLUSIVE region: other cells may also sit there).  The only long hop left is the one whose
# launch can absorb it (OT_RLF_GROUPS includes cap: the macro rd_out -> cap hop, launched by the macro's clk->q
# ~490 ps FF; otherwise cap -> xa / xa -> cap2x, logic hops); every zero-logic shift hop is local and the sink field is
# compact.  Exact RTL, zero added edges: placement only.  Sourced in PRE_GLOBAL_PLACE (spec pin_hook_before_flops).
set rlf_block [ord::get_db_block]
set rlf_dbu [$rlf_block getDbUnitsPerMicron]
set rlf_groups [expr {[info exists ::env(OT_RLF_GROUPS)] ? $::env(OT_RLF_GROUPS) : "cap xa sel_r cap2x g"}]
if {![info exists ::env(OT_RLF_BOXES)] || [llength $::env(OT_RLF_BOXES)] % 4 != 0 || [llength $::env(OT_RLF_BOXES)] == 0} {
  error "romleaf_field_region: OT_RLF_BOXES must hold x0 y0 x1 y1 [...] um"
}
set rlf_pat [dict create \
  cap   {^u_lg\.g_pair\[0\]\.g_bank\.cap\[[0-9]+\]} \
  xa    {^u_lg\.g_pair\[0\]\.g_bank\.g_capx2\.xa_(s|m|p|nz)\[[0-9]+\]} \
  sel_r {^u_lg\.g_pair\[0\]\.g_bank\.g_capx2\.sel_r\[[0-9]+\]} \
  cap2x {^u_lg\.g_pair\[0\]\.g_bank\.g_capx2\.cap2x\[[0-9]+\]} \
  g     {^u_lg\.g_pair\[0\]\.g\[[0-9]+\]}]
set rlf_expect [dict create cap 256 xa 384 sel_r 8 cap2x 512 g 512]
set rlf_region [odb::dbRegion_create $rlf_block ot_rlf_field]
$rlf_region setRegionType INCLUSIVE
set rlf_area 0.0
foreach {x0 y0 x1 y1} $::env(OT_RLF_BOXES) {
  odb::dbBox_create $rlf_region [expr {round($x0*$rlf_dbu)}] [expr {round($y0*$rlf_dbu)}] [expr {round($x1*$rlf_dbu)}] [expr {round($y1*$rlf_dbu)}]
  set rlf_area [expr {$rlf_area + ($x1-$x0)*($y1-$y0)}]
}
set rlf_grp [odb::dbGroup_create $rlf_region ot_rlf_field]
set rlf_n [dict create]
set rlf_cell_area 0.0
foreach inst [$rlf_block getInsts] {
  set m [$inst getMaster]
  if {[$m isBlock] || ![$m isSequential]} continue
  set name [string map [list "\\" ""] [$inst getName]]
  foreach k $rlf_groups {
    if {[regexp [dict get $rlf_pat $k] $name]} {
      if {[$inst getGroup] ne "NULL" && [$inst getGroup] ne ""} { error "romleaf_field_region: already grouped: $name" }
      $rlf_grp addInst $inst
      dict incr rlf_n $k
      set rlf_cell_area [expr {$rlf_cell_area + double([$m getWidth])*[$m getHeight]/($rlf_dbu*$rlf_dbu)}]
      break
    }
  }
}
foreach k $rlf_groups {
  set n [expr {[dict exists $rlf_n $k] ? [dict get $rlf_n $k] : 0}]
  # xa: 32 bytes x (s 1 + m 8 + p 3 + nz 1) = 416 bits; synthesis may merge constant / duplicate bits, so xa and cap are
  # checked for presence (>= half) and the exact groups for their count
  if {$k in {g cap2x} && $n != [dict get $rlf_expect $k]} { error "romleaf_field_region: $k has $n flops, expected [dict get $rlf_expect $k]" }
  if {$n < [dict get $rlf_expect $k] / 2} { error "romleaf_field_region: $k has only $n flops" }
}
puts "OT_RLF field [format %.0f $rlf_area] um2 boxes {$::env(OT_RLF_BOXES)} groups {$rlf_groups} members $rlf_n flop_area [format %.1f $rlf_cell_area] um2"
