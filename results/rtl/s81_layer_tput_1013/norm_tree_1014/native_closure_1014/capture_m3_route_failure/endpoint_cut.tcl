read_db [lindex [glob /work/results/asap7/*/base/5_1_grt-failed.odb] 0]
set blk [ord::get_db_block]
set f [open /out/endpoint_boxes.tsv w]
foreach net [$blk getNets] {
  set xs {}; set ys {}
  foreach it [$net getITerms] {
    set b [[$it getInst] getBBox]
    lappend xs [expr {([$b xMin] + [$b xMax]) / 2.0}]
    lappend ys [expr {([$b yMin] + [$b yMax]) / 2.0}]
  }
  foreach bt [$net getBTerms] {
    set b [$bt getBBox]
    lappend xs [expr {([$b xMin] + [$b xMax]) / 2.0}]
    lappend ys [expr {([$b yMin] + [$b yMax]) / 2.0}]
  }
  if {[llength $xs] < 2} continue
  set xs [lsort -real $xs]; set ys [lsort -real $ys]
  puts $f "[$net getName]\t[$net getSigType]\t[lindex $xs 0]\t[lindex $xs end]\t[lindex $ys 0]\t[lindex $ys end]"
}
close $f
exit
