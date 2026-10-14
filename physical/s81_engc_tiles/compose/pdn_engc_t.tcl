# dsfd_engram_c ALL-TILE PDN (el1011-ds-misc/engram 2026-10-11; the SRAMs now live inside the bank tiles, whose own
# pdn_view_sram.tcl grids connect them)  -- derived from the HIER PDN = physical/s81_ph_views/common/pdn_view.tcl + a macro grid for the hardened leaves
# SLIVER ROWS (el1013-s81-engram 2026-10-13, CTS-stop run c1: PDN-0178/0179 "Remaining channel (0, 201.4)-(0.55, 223.3)
# on M6").  The row cut (2.052 um around every child) leaves 0.54 um rows between the W die edge and u_ws / u_pb1
# (x 2.592: the HBM pin seam) and 2.27 um rows in the other edge seams.  Their M5 strap (x 0.3) cannot reach M6 where the
# die's M6 pins stand, and no M6 pair fits a 0.55 um channel.  Nothing is ever placed there (5 um macro halo), so the
# rows narrower than 4 um go, with their tap / endcap cells, before the grid is built; the M5 straps start at 2.988
# (= 0.3 + 56 tracks: inside the children's cut along the W edge, unchanged pitch elsewhere).
set ot_b [ord::get_db_block]; set ot_k 0; set ot_rr {}
foreach ot_r [$ot_b getRows] {
  set ot_bb [$ot_r getBBox]
  if {[$ot_bb xMax] - [$ot_bb xMin] < 4000} { lappend ot_rr [list [$ot_bb xMin] [$ot_bb yMin] [$ot_bb xMax] [$ot_bb yMax]]; odb::dbRow_destroy $ot_r; incr ot_k }
}
set ot_c 0
if {$ot_k > 0} {
  foreach ot_i [$ot_b getInsts] {
    if {[[$ot_i getMaster] isBlock]} { continue }
    set ot_bb [$ot_i getBBox]
    foreach ot_q $ot_rr {
      lassign $ot_q a0 b0 a1 b1
      if {[$ot_bb xMin] >= $a0 && [$ot_bb xMax] <= $a1 && [$ot_bb yMin] >= $b0 && [$ot_bb yMax] <= $b1} { odb::dbInst_destroy $ot_i; incr ot_c; break }
    }
  }
}
puts "OT_PDN_SLIVER rows removed $ot_k (narrower than 4 um), physical cells removed $ot_c"
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {2.988}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
# HIER leaves (closed dsfd_engram_lkp / dsfd_engram_sink views: OBS M1..M7, VDD / VSS pins on M6 / M7 with M7 vertical
# stripes at pitch 10.8): the ORFS BLOCKS recipe one layer up -- the top grid carries M8 straps over the whole outline
# (connected to its M7), and the leaf grid connects each leaf's M7 pins to those M8 straps (PDN-0232/0233 otherwise:
# a leaf grid with only a connect and no layer above the leaf's obstructions has no shapes).
add_pdn_stripe -grid {top} -layer {M8} -width {0.32} -spacing {5.08} -pitch {10.8} -offset {2.0}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -macro -cells {dsfd_engram_lkp dsfd_engram_sink ot_engc_t_win ot_engc_t_io ot_engc_t_ws ot_engc_t_pbb ot_engc_t_pbc} -halo {2 2 2 2} -voltage_domains {CORE} -name {engram_leaves}
add_pdn_connect -grid {engram_leaves} -layers {M7 M8}
