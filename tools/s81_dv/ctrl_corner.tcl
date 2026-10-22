# S81 measured RRD corner remedy. Buffers only, actual placed pins and bodies.
# Called after spread and before complete-payload forwarded-clock balancing.
proc s81_cc_xy {it} {
 set bb [$it getBBox]
 return [list [expr {([$bb xMin]+[$bb xMax])/2.0}] [expr {([$bb yMin]+[$bb yMax])/2.0}]]
}
proc s81_cc_legal {p q box} {
 lassign $p x y; lassign $q a c; lassign $box x0 y0 x1 y1
 if {$x==$a} {return [expr {!($x0<$x && $x<$x1 && min($y,$c)<$y1 && max($y,$c)>$y0)}]}
 if {$y==$c} {return [expr {!($y0<$y && $y<$y1 && min($x,$a)<$x1 && max($x,$a)>$x0)}]}
 return 0
}
proc s81_cc_path {a z box margin} {
 lassign $a ax ay; lassign $z zx zy; lassign $box x0 y0 x1 y1
 set options [list [list $a [list [expr {$x1+$margin}] $ay] [list [expr {$x1+$margin}] $zy] $z] \
 [list $a [list [expr {$x0-$margin}] $ay] [list [expr {$x0-$margin}] $zy] $z] \
 [list $a [list $ax [expr {$y1+$margin}]] [list $zx [expr {$y1+$margin}]] $z] \
 [list $a [list $ax [expr {$y0-$margin}]] [list $zx [expr {$y0-$margin}]] $z]]
 set best {};set bestlen 1e30
 foreach path $options {
  set ok 1;set length 0
  foreach p [lrange $path 0 end-1] q [lrange $path 1 end] {
   if {![s81_cc_legal $p $q $box]} {set ok 0;break}
   set length [expr {$length+abs([lindex $p 0]-[lindex $q 0])+abs([lindex $p 1]-[lindex $q 1])}]
  }
  if {$ok && $length<$bestlen} {set best $path;set bestlen $length}
 }
 if {![llength $best]} {error "S81_RRD_NO_PERIMETER_PATH $a $z $box"}
 return $best
}
proc s81_ctrl_corner_repair {prefix} {
 set blk [ord::get_db_block];set dbu [$blk getDbUnitsPerMicron]
 set buf [[ord::get_db] findMaster BUFx8_ASAP7_75t_R]
 set todo {};set roots 0;set traced 0
 foreach ctrl [$blk getInsts] {
  if {[[$ctrl getMaster] getName] ne "dsfd_ctrl_rg3"} continue
  set bb [$ctrl getBBox];set box [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
  foreach pin [$ctrl getITerms] {
   if {[$pin getIoType] ne "OUTPUT" || ![string match {rrd\[*\]} [[$pin getMTerm] getName]]} continue
   incr roots;set queue [list $pin];set seen [dict create];set at 0
   while {$at<[llength $queue]} {
    set drv [lindex $queue $at];incr at;set net [$drv getNet]
    if {$net eq "NULL" || [dict exists $seen [$net getName]]} continue
    dict set seen [$net getName] 1;incr traced
    set a [s81_cc_xy $drv]
    foreach sink [$net getITerms] {
     if {[$sink getIoType] ne "INPUT"} continue
     set z [s81_cc_xy $sink]
     set length [expr {abs([lindex $a 0]-[lindex $z 0])+abs([lindex $a 1]-[lindex $z 1])}]
     if {$length>405.0*$dbu} {lappend todo [list $drv $sink $box [$ctrl getName] [[$pin getMTerm] getName] [expr {$length/$dbu}]]}
     set inst [$sink getInst];set mst [[$inst getMaster] getName]
     if {[string match BUFx* $mst] || [string match INVx* $mst]} {
      foreach p [$inst getITerms] {if {[$p getIoType] eq "OUTPUT"} {lappend queue $p}}
     }
    }
   }
  }
 }
 set added {};set rows {};set k 0
 foreach item $todo {
  lassign $item drv sink box root pin oldlen
  set a [s81_cc_xy $drv];set z [s81_cc_xy $sink]
  set path [s81_cc_path $a $z $box [expr {8*$dbu}]];set pts {}
  foreach p [lrange $path 0 end-1] q [lrange $path 1 end] {
   lassign $p x y;lassign $q x1 y1
   set n [expr {max(1,int(ceil((abs($x-$x1)+abs($y-$y1))/(120.0*$dbu))))}]
   for {set j 1} {$j<=$n} {incr j} {lappend pts [list [expr {$x+($x1-$x)*$j/double($n)}] [expr {$y+($y1-$y)*$j/double($n)}]]}
  }
  set pts [lrange $pts 0 end-1];set prev [$drv getNet];$sink disconnect;set cells {}
  foreach p $pts {
   set name "s81_rrd_corner_[incr k]"
   while {[$blk findInst $name] ne "NULL" || [$blk findNet ${name}_y] ne "NULL"} {set name "s81_rrd_corner_[incr k]"}
   set inst [odb::dbInst_create $blk $buf $name]
   $inst setLocation [expr {int([lindex $p 0]-[$buf getWidth]/2)}] [expr {int([lindex $p 1]-[$buf getHeight]/2)}];$inst setPlacementStatus PLACED
   set nn [odb::dbNet_create $blk ${name}_y]
   foreach it [$inst getITerms] {
    if {[[$it getMTerm] getSigType] in {POWER GROUND}} continue
    if {[$it getIoType] eq "INPUT"} {$it connect $prev} elseif {[$it getIoType] eq "OUTPUT"} {$it connect $nn}
   }
   set prev $nn;lappend added $inst;lappend cells $inst
  }
  $sink connect $prev;lappend rows [list $drv $sink $cells $root $pin $oldlen]
 }
 set unplaced [ot_die_rep_spread $added ${prefix}.spread.json]
 set bad 0;set largest 0;set details {}
 foreach row $rows {
  lassign $row drv sink cells root pin oldlen;set last [s81_cc_xy $drv];set mx 0
  foreach inst $cells {
   foreach it [$inst getITerms] {if {[$it getIoType] eq "INPUT"} {set inp $it} elseif {[$it getIoType] eq "OUTPUT"} {set outp $it}}
   set p [s81_cc_xy $inp];set length [expr {(abs([lindex $last 0]-[lindex $p 0])+abs([lindex $last 1]-[lindex $p 1]))/$dbu}]
   set mx [expr {max($mx,$length)}];set last [s81_cc_xy $outp]
  }
  set p [s81_cc_xy $sink];set mx [expr {max($mx,(abs([lindex $last 0]-[lindex $p 0])+abs([lindex $last 1]-[lindex $p 1]))/$dbu)}]
  if {$mx>160} {incr bad};set largest [expr {max($largest,$mx)}]
  lappend details "{\"root\":[ot_die_rep_json_str $root],\"pin\":[ot_die_rep_json_str $pin],\"old_um\":$oldlen,\"new_max_um\":$mx,\"buffers\":[llength $cells]}"
 }
 set f [open ${prefix}.json w]
 puts $f "{\"rule\":\"Actual controller RRD legal perimeter buffers; no added protocol edges\",\"roots\":$roots,\"nets_traced\":$traced,\"repaired_branches\":[llength $rows],\"buffers\":[llength $added],\"unplaced\":$unplaced,\"segments_over160\":$bad,\"max_segment_um\":$largest,\"rows\":\[[join $details ,]\]}";close $f
 puts "S81_CTRL_CORNER roots=$roots traced=$traced branches=[llength $rows] buffers=[llength $added] unplaced=$unplaced over160=$bad max_um=$largest";flush stdout
 return [expr {$bad+$unplaced}]
}
# Physical callers retain global power connection rules for newly created cells.
