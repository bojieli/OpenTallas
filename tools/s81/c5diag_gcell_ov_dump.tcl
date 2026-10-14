# c5 diagnosis (2026-10-13): PER-GCELL sparse overflow dump from a GRT checkpoint (gcell_dump.tcl sums 4x4 blocks and
# so hides ~half of the overflow).  Mount the run's grt dir read-only at /in and a scratch dir at /out.
#   O <layer> <i> <j> <cap> <use>     every gcell with use > cap
#   A <layer> <I> <J> <cap> <use>     50x50-gcell (480 um) aggregates, all gcells
#   C / U <layer> <j> v0 v1 ...       full capacity / usage rows (M6..M9 only)
# NOTE (measured on c3/c5): the odb stores capacity = raw tracks and usage = net usage + reductions (blockage,
# layer adjustment) in 8 bits, so usage wraps mod 256 exactly where the overflow is worst (M6 > 105, M8 > 135) and the
# M4/M5 rows are not usable (their reductions alone wrap).  c5diag_congestion.py unwraps M6..M9 with the guide usage.
read_db /in/ckpt_grt.odb
set blk [ord::get_db_block]
set out [open /out/gcell_ov.txt w]
set grid [$blk getGCellGrid]
set gx [$grid getGridX]; set gy [$grid getGridY]
puts $out "GRIDX [join $gx ,]"
puts $out "GRIDY [join $gy ,]"
set tech [ord::get_db_tech]
set nx [llength $gx]; set ny [llength $gy]
set B 50
foreach ln {M4 M5 M6 M7 M8 M9} {
  set layer [$tech findLayer $ln]
  set tot 0
  set full [expr {[lsearch {M6 M7 M8 M9} $ln] >= 0}]
  for {set J 0} {$J*$B < $ny} {incr J} {
    array unset ac; array unset au
    set j1 [expr {min(($J+1)*$B,$ny)}]
    for {set j [expr {$J*$B}]} {$j < $j1} {incr j} {
      set rc {}; set ru {}
      for {set i 0} {$i < $nx} {incr i} {
        set c [$grid getCapacity $layer $i $j]; set u [$grid getUsage $layer $i $j]
        if {$full} { lappend rc [expr {int($c)}]; lappend ru [expr {int($u)}] }
        set I [expr {$i/$B}]
        if {[info exists ac($I)]} { set ac($I) [expr {$ac($I)+$c}]; set au($I) [expr {$au($I)+$u}] } else { set ac($I) $c; set au($I) $u }
        if {$u > $c} { puts $out "O $ln $i $j [expr {int($c)}] [expr {int($u)}]"; set tot [expr {$tot+$u-$c}] }
      }
      if {$full} { puts $out "C $ln $j [join $rc { }]"; puts $out "U $ln $j [join $ru { }]" }
    }
    foreach I [lsort -integer [array names ac]] { puts $out "A $ln $I $J [expr {int($ac($I))}] [expr {int($au($I))}]" }
  }
  puts "OT_GCELL_OV layer=$ln overflow=$tot"; flush stdout
}
close $out
puts "OT_GCELL_OV done nx=$nx ny=$ny"
