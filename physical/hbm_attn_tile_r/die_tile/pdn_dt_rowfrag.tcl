# safe-hbm 2026-10-08 (REVIEW_20261008 C6, flow fix): hfd_attn_half_hi died in 2_4_floorplan_pdn with PDN-0179
# ("Unable to repair all channels"): the staggered u_res sn banks (right edge 1763.6..1764.4) and the edge ew bank u_oo
# (1766.592) leave std-cell row fragments of 7 sites (1765.206..1765.584) whose M1/M2 followpins pdngen cannot join,
# and a 0.6 um gap between two u_xr sn bank halos leaves an M6 stub.  Row fragments narrower than ot_min_row_um can hold
# no useful logic (the SLIVER blockages cover them after PDN anyway); delete them, and the tap cells standing on them,
# before the grid is built, then build the unchanged die-tile grid.  Checked on the failed run's 2_3_floorplan_tapcell
# odb: 405 fragments < 5 um removed, pdngen OK (PDN-0178 x3 / PDN-0179 before).
set ot_min_row_um [expr {[info exists ::env(OT_MIN_ROW_UM)] ? $::env(OT_MIN_ROW_UM) : 5.0}]
set ot_blk [ord::get_db_block]
set ot_dbu [[$ot_blk getTech] getDbUnitsPerMicron]
set ot_frag {}
foreach ot_r [$ot_blk getRows] {
  set ot_b [$ot_r getBBox]
  if {([$ot_b xMax] - [$ot_b xMin]) / double($ot_dbu) < $ot_min_row_um} {
    lappend ot_frag [list [$ot_b xMin] [$ot_b yMin] [$ot_b xMax] [$ot_b yMax]]
    odb::dbRow_destroy $ot_r
  }
}
set ot_ntap 0
if {[llength $ot_frag]} {
  foreach ot_i [$ot_blk getInsts] {
    if {[[$ot_i getMaster] isBlock]} {continue}
    set ot_ib [$ot_i getBBox]
    foreach ot_f $ot_frag {
      lassign $ot_f x0 y0 x1 y1
      if {[$ot_ib xMin] >= $x0 && [$ot_ib xMax] <= $x1 && [$ot_ib yMin] >= $y0 && [$ot_ib yMax] <= $y1} {
        odb::dbInst_destroy $ot_i; incr ot_ntap; break
      }
    }
  }
}
puts "OT_ROW_FRAG removed [llength $ot_frag] rows narrower than $ot_min_row_um um and $ot_ntap cells on them"
source /src/physical/hbm_attn_tile_r/die_tile/pdn_dt.tcl
