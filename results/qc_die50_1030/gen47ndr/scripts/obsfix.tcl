# DIE-QC-50/gen47ndr measurement-DB fix (NOT a plan change; this DB only).  Every block (abstract) master of the native
# source carries a FULL-outline OBS on M1-M3, while its M4/M5 OBS leave the partition street cross open (the planned
# clock-cell sites).  Clock cells in those streets are therefore shorted on M1-M3 at their pins by DRT (probe_D:
# 'Short inst:c_E1_bn_11 net:ck_n8041 on M1/M2/M3').  dbBox_destroy does not remove master OBS, so each block master
# is CLONED into lib otfix (same size, same mterms/pins/shapes) with M1-M3 OBS := its own M4 OBS rects, and every
# instance is re-created on the clone (same name/location/orient/status/connections; swapMaster segfaults in 26Q3).  Masters whose M4 OBS is a single rect (no street) are cloned unchanged.
set tech [ord::get_db_tech]
set fl [odb::dbLib_create [ord::get_db] otfix $tech "/"]
set nm 0; set nsh 0; set nobs 0
set map {}
foreach lib [[ord::get_db] getLibs] {
  if {[$lib getName] eq "otfix"} continue
  foreach m [$lib getMasters] {
    if {![$m isBlock]} continue
    set nn "[$m getName]__otfix"
    set f [odb::dbMaster_create $fl $nn]
    $f setType [$m getType]
    $f setWidth [$m getWidth]; $f setHeight [$m getHeight]
    foreach t [$m getMTerms] {
      set ft [odb::dbMTerm_create $f [$t getName] [$t getIoType] [$t getSigType]]
      foreach p [$t getMPins] {
        set fp [odb::dbMPin_create $ft]
        foreach g [$p getGeometry] { set L [$g getTechLayer]; if {$L ne "NULL"} { odb::dbBox_create $fp $L [$g xMin] [$g yMin] [$g xMax] [$g yMax]; incr nsh } }
      }
    }
    set r4 {}
    foreach o [$m getObstructions] { if {[[$o getTechLayer] getName] eq "M4"} { lappend r4 [list [$o xMin] [$o yMin] [$o xMax] [$o yMax]] } }
    set street [expr {[llength $r4] >= 2}]
    foreach o [$m getObstructions] {
      set L [$o getTechLayer]
      if {$street && [$L getName] in {M1 M2 M3}} continue
      if {$L ne "NULL"} { odb::dbBox_create $f $L [$o xMin] [$o yMin] [$o xMax] [$o yMax]; incr nobs }
    }
    if {$street} { foreach ln {M1 M2 M3} { set L [$tech findLayer $ln]; foreach r $r4 { lassign $r a c d e; odb::dbBox_create $f $L $a $c $d $e; incr nobs } } }
    $f setFrozen
    dict set map [$m getName] [list $f $street]
    incr nm
  }
}
set ns 0; set nst 0
set blk [ord::get_db_block]
foreach i [$blk getInsts] {
  set mn [[$i getMaster] getName]
  if {![dict exists $map $mn]} continue
  lassign [dict get $map $mn] f st
  set nm_ [$i getName]; lassign [$i getLocation] x y; set ori [$i getOrient]; set ps [$i getPlacementStatus]
  set conns {}
  foreach it [$i getITerms] { set n [$it getNet]; if {$n ne "NULL"} { lappend conns [list [[$it getMTerm] getName] $n] } }
  odb::dbInst_destroy $i
  set ni [odb::dbInst_create $blk $f $nm_]
  $ni setOrient $ori; $ni setLocation $x $y; $ni setPlacementStatus $ps
  foreach c $conns { lassign $c tn n; [$ni findITerm $tn] connect $n }
  incr ns; incr nst $st
}
puts "OBSFIX masters $nm pin_shapes $nsh obs $nobs insts_replaced $ns street_insts $nst"
