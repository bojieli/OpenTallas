read_db $::env(DB)
set blk [ord::get_db_block]
set k $::env(K)
set dbu [$blk getDefUnits]
foreach {tag pat} [list src "u_bound.u_u_xh${k}.n_d*" face "u_bound.u_bout_cw_n${k}/q*" xh "u_bound.u_u_xh${k}.*"] {
  set n 0; set sx 0; set sy 0; set x0 1e18; set y0 1e18; set x1 -1e18; set y1 -1e18
  foreach i [$blk getInsts] {
    if {![string match $pat [$i getName]]} continue
    set b [$i getBBox]; set x [expr {([$b xMin]+[$b xMax])/2.0/$dbu}]; set y [expr {([$b yMin]+[$b yMax])/2.0/$dbu}]
    incr n; set sx [expr {$sx+$x}]; set sy [expr {$sy+$y}]
    if {$x<$x0} {set x0 $x}; if {$y<$y0} {set y0 $y}; if {$x>$x1} {set x1 $x}; if {$y>$y1} {set y1 $y}
  }
  if {$n} { puts [format "CENT %s n %d c %.1f %.1f bbox %.1f %.1f %.1f %.1f" $tag $n [expr {$sx/$n}] [expr {$sy/$n}] $x0 $y0 $x1 $y1] } else { puts "CENT $tag n 0" }
}
exit
