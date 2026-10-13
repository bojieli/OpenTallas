# Dump GRT gcell capacity/usage (4x4 gcell blocks) from a checkpoint odb: format = HBM gcell_usage.txt (winov.py)
read_db /work/ckpt_grt.odb
# usage: hand the run's grt dir as /work (ckpt_grt.odb inside); writes /work/gcell_usage.txt
set blk [ord::get_db_block]
set out [open /work/gcell_usage.txt w]
set grid [$blk getGCellGrid]
set gx [$grid getGridX]; set gy [$grid getGridY]
puts $out "GRIDX [join $gx ,]"
puts $out "GRIDY [join $gy ,]"
set tech [ord::get_db_tech]
set nx [llength $gx]; set ny [llength $gy]
foreach ln {M4 M5 M6 M7 M8 M9} {
  set layer [$tech findLayer $ln]
  for {set j 0} {$j < $ny} {incr j 4} {
    set row {}
    for {set i 0} {$i < $nx} {incr i 4} {
      set cap 0; set use 0
      for {set jj $j} {$jj < min($j+4,$ny)} {incr jj} {
        for {set ii $i} {$ii < min($i+4,$nx)} {incr ii} {
          set cap [expr {$cap + [$grid getCapacity $layer $ii $jj]}]
          set use [expr {$use + [$grid getUsage $layer $ii $jj]}]
        }
      }
      lappend row "$cap/$use"
    }
    puts $out "L $ln $j [join $row { }]"
  }
}
close $out
puts "OT_GCELL_DUMP done nx=$nx ny=$ny"
