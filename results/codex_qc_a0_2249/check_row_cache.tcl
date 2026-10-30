# Reference comparison includes duplicate/disordered row chunks and exact half-row ties.
source [file join [file dirname [info script]] late_row_cache.tcl]
set ::row_calls 0
set ::allrows {}
foreach {id y} {r0 720 r1 0 r2 1080 r3 360 r4 720 r5 1440 r6 -360 r7 1800} {
  set ::row_y($id) $y
  proc $id {method args} [format {
    if {$method ne "getOrigin"} {error "unexpected row method"}
    incr ::row_calls
    return [list 0 %s]
  } $y]
  lappend ::allrows $id
}
proc block {method args} {if {$method ne "getRows"} {error "unexpected block method"};return $::allrows}
set ::ot_ci_b block
proc reference {target height} {
  set row "";set best 1e99
  foreach r [$::ot_ci_b getRows] {
    lassign [$r getOrigin] rx ry
    set d [expr {abs($ry+$height/2.0-$target)}]
    if {$d<$best} {set best $d;set row $r}
  }
  return $row
}
set tested 0
foreach h {1 270 360 720} {
  foreach target {-2000 -1000 -360 -180 0 1 179.5 180 360 540 720 900 1080 1440 1800 3000} {
    set ref [reference $target $h]
    set fast [ot_ci_late_nearest_row $target $h]
    if {$ref ne $fast} {error "mismatch at target=$target height=$h: $ref != $fast"}
    incr tested
  }
}
puts "ROW_CACHE_EQUIVALENT $tested duplicate/disordered/boundary/tie cases; cached row inventory scanned once"
