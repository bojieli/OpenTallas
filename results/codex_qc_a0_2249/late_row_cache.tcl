# Candidate helper for core_infra_late.tcl; not sourced by the active pinned CTS.
# Preserves nearest-row selection and original OpenDB row-order tie breaking.
# Call unset -nocomplain ::ot_ci_late_row_cache at core_infra_late.tcl load.
proc ot_ci_late_nearest_row {target_y height} {
  if {![info exists ::ot_ci_late_row_cache]} {
    set records {};set first {};set index 0
    foreach r [$::ot_ci_b getRows] {
      lassign [$r getOrigin] rx ry
      if {![dict exists $first $ry]} {
        dict set first $ry 1
        lappend records [list $ry $index $r]
      }
      incr index
    }
    set ::ot_ci_late_row_cache [lsort -integer -index 0 $records]
  }
  set rows $::ot_ci_late_row_cache
  set n [llength $rows]
  if {!$n} {return ""}
  set target [expr {$target_y - $height/2.0}]
  set lo 0;set hi $n
  while {$lo < $hi} {
    set mid [expr {($lo+$hi)/2}]
    if {[lindex $rows $mid 0] < $target} {set lo [expr {$mid+1}]} else {set hi $mid}
  }
  set best 1e99;set order 1e99;set row ""
  foreach k [list [expr {$lo-1}] $lo] {
    if {$k < 0 || $k >= $n} continue
    lassign [lindex $rows $k] ry index r
    set d [expr {abs($ry+$height/2.0-$target_y)}]
    if {$d < $best || ($d == $best && $index < $order)} {
      set best $d;set order $index;set row $r
    }
  }
  return $row
}
