# ndr.fat_vias (opt-in, HUBMESH-7): copy of each LEF via with its pads on the NDR layers widened to the NDR wire
# width (square), so an NDR wire meets its via/pin stack without the sub-MINSTEP jogs DRT cannot remove
proc ot_fat_via {src w layers} {
  set tech [ord::get_db_tech]
  set s [$tech findVia $src]
  if {$s == "NULL"} { error "ndr.fat_vias: no via $src in the tech LEF" }
  set v [odb::dbTechVia_create $tech ${src}_F]
  set h [expr {$w / 2}]
  foreach b [$s getBoxes] {
    set L [$b getTechLayer]
    if {[lsearch -exact $layers [$L getName]] >= 0 && [$L getType] eq "ROUTING"} {
      odb::dbBox_create $v $L [expr {-$h}] [expr {-$h}] $h $h
    } else {
      odb::dbBox_create $v $L [$b xMin] [$b yMin] [$b xMax] [$b yMax]
    }
  }
}
ot_fat_via VIA78 240 {M8 M9}
ot_fat_via VIA89 240 {M8 M9}
create_ndr -name CONTACT -width {M8 0.24 M9 0.24} -spacing {M8 0.32 M9 0.32} -via {VIA78_F VIA89_F}
