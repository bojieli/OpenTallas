read_db /b/3_place.odb
set blk [ord::get_db_block]
set dbu [$blk getDefUnits]
set out [open /o/rst_hops.tsv w]
foreach inst [$blk getInsts] {
  set n [$inst getName]
  if {![string match "*ot_r*" $n]} continue
  if {[$inst getPlacementStatus] ne "FIRM" && [$inst getPlacementStatus] ne "LOCKED"} {}
  set m [[$inst getMaster] getName]
  if {![string match "DFF*" $m] && ![string match "*dff*" $m]} continue
  set loc [$inst getLocation]
  foreach it [$inst getITerms] {
    if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
    set net [$it getNet]; if {$net eq "NULL"} continue
    set mx 0; set nl 0; set far ""
    foreach t [$net getITerms] {
      if {[[$t getMTerm] getIoType] ne "INPUT"} continue
      set i2 [$t getInst]; set l2 [$i2 getLocation]
      set d [expr {(abs([lindex $l2 0]-[lindex $loc 0])+abs([lindex $l2 1]-[lindex $loc 1]))/double($dbu)}]
      incr nl; if {$d > $mx} {set mx $d; set far [$i2 getName]}
    }
    puts $out "$n\t$m\t[$inst getPlacementStatus]\t$nl\t[format %.1f $mx]\t$far"
  }
}
close $out
