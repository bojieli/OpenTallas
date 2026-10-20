# S81-COLL5 v8 lane kits (dscoll_lane_{w,e}_s5{,c}): keep the std-cell rows of ONE full-width band y 259.2..340.2 and
# of two full-height face columns x <= 37.8 / x >= 688.0 (core edge .. first/last macro column halo), joined to the
# band; every other row is removed before tapcell (checklist 6: no std cell in a macro channel; face pin cells at
# their pins).  Rows outside the band are re-created as the two face segments on the original site grid.
set ot_cb [ord::get_db_block]
set ot_cd [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_by0 [expr {round(259.2*$ot_cd)}]
set ot_by1 [expr {round(340.2*$ot_cd)}]
set ot_fx0 [expr {round(37.8*$ot_cd)}]
set ot_fx1 [expr {round(688.0*$ot_cd)}]
set ot_new {}
set ot_old {}
set ot_keep 0
foreach row [$ot_cb getRows] {
  set bb [$row getBBox]
  if {[$bb yMin] >= $ot_by0 && [$bb yMax] <= $ot_by1} { incr ot_keep; continue }
  set site [$row getSite]
  set org [$row getOrigin]
  set ox [lindex $org 0]; set oy [lindex $org 1]
  set sp [$row getSpacing]
  set n [$row getSiteCount]
  set nl [expr {($ot_fx0 - $ox) / $sp}]
  set kr [expr {($ot_fx1 - $ox + $sp - 1) / $sp}]
  lappend ot_new [list [$row getName] $site $ox $oy [$row getOrient] $sp $nl $kr $n]
  lappend ot_old $row
}
foreach row $ot_old { odb::dbRow_destroy $row }
set ot_seg 0
foreach r $ot_new {
  lassign $r nm site ox oy orient sp nl kr n
  if {$nl > 0} {
    odb::dbRow_create $ot_cb "${nm}_fl" $site $ox $oy $orient HORIZONTAL $nl $sp; incr ot_seg
  }
  if {$kr < $n} {
    odb::dbRow_create $ot_cb "${nm}_fr" $site [expr {$ox + $kr*$sp}] $oy $orient HORIZONTAL [expr {$n - $kr}] $sp; incr ot_seg
  }
}
if {$ot_keep == 0 || $ot_seg == 0} { error "COLL_S5_CELL_BAND band rows=$ot_keep face segments=$ot_seg" }
puts "COLL_S5_CELL_BAND band_rows=$ot_keep face_segments=$ot_seg replaced=[llength $ot_old] band y259.2..340.2 faces x<=37.8 x>=688.0"
