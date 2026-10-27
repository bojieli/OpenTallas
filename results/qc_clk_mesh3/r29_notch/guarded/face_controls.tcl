read_db /out/coupon_native.odb
set blk [ord::get_db_block]
set tech [ord::get_db_tech]
set ::ot_clock_shield_swires {}
proc ot_shield_box {sw ly x0 y0 x1 y1 outer nominal} {
 set b [odb::dbSBox_create $sw $ly $x0 $y0 $x1 $y1 STRIPE]
 set ::ot_clock_shield_outer($b) $outer;set ::ot_clock_shield_nominal($b) $nominal
 return $b
}
set nn [odb::dbNet_create $blk VSS_SAFE]
$nn setSpecial
set ss [odb::dbSWire_create $nn ROUTED]
set ps [odb::dbSWire_create $nn ROUTED]
lappend ::ot_clock_shield_swires $ss
ot_shield_box $ss [$tech findLayer M9] 0 0 640 1000 2 640
ot_shield_box $ss [$tech findLayer M9] 0 500 640 1500 2 640
odb::dbSBox_create $ps [$tech findLayer M9] 660 -100 1140 1600 STRIPE
proc ot_merge_shields {netname wdbu} { global blk; set n [$blk findNet $netname]; array set g {}; foreach sw [$n getSWires] { foreach b [$sw getWires] { if {[$b isVia]} { continue }; set ly [[$b getTechLayer] getName]; if {$ly ne "M8" && $ly ne "M9"} { continue }; set dx [$b getDX]; set dy [$b getDY]; if {$dy > $dx} { if {$dx != $wdbu} { continue }; lappend g($ly,V,[$b xMin],[$b xMax]) [list [$b yMin] [$b yMax] $b $sw] } else { if {$dy != $wdbu} { continue }; lappend g($ly,H,[$b yMin],[$b yMax]) [list [$b xMin] [$b xMax] $b $sw] } } }; set nin 0; set nout 0; foreach k [array names g] { if {[llength $g($k)] < 2} { continue }; lassign [split $k ,] ly dir c0 c1; set l [[ord::get_db_tech] findLayer $ly]; set runs {}; set cur {}; foreach it [lsort -integer -index 0 $g($k)] { lassign $it lo hi b sw; if {[llength $cur] && $lo <= [lindex $cur 1]} { lset cur 1 [expr {max([lindex $cur 1], $hi)}]; lset cur 2 [concat [lindex $cur 2] [list $b]] } else { if {[llength $cur]} { lappend runs $cur }; set cur [list $lo $hi [list $b] $sw] } }; lappend runs $cur; foreach r $runs { lassign $r lo hi bs sw; if {[llength $bs] < 2} { continue }; incr nin [llength $bs]; incr nout; set face {}; set nominal {}; set safe 1; foreach b $bs { if {![info exists ::ot_clock_shield_outer($b)] || ![info exists ::ot_clock_shield_nominal($b)]} {set safe 0} elseif {$face eq {}} {set face $::ot_clock_shield_outer($b);set nominal $::ot_clock_shield_nominal($b)} elseif {$face ne $::ot_clock_shield_outer($b) || $nominal ne $::ot_clock_shield_nominal($b)} {set safe 0}; unset -nocomplain ::ot_clock_shield_outer($b) ::ot_clock_shield_nominal($b);odb::dbSBox_destroy $b }; if {$dir eq "V"} { set merged [odb::dbSBox_create $sw $l $c0 $lo $c1 $hi STRIPE] } else { set merged [odb::dbSBox_create $sw $l $lo $c0 $hi $c1 STRIPE] }; if {$safe} {set ::ot_clock_shield_outer($merged) $face;set ::ot_clock_shield_nominal($merged) $nominal} } }; puts "OT_SHIELD_MERGE in $nin out $nout" }
ot_merge_shields VSS_SAFE [expr {round(0.64*[[ord::get_db_block] getDbUnitsPerMicron])}]
proc ot_trim_shield_notches {netname wdbu gap} {
 global blk
 if {![info exists ::ot_clock_shield_swires]} {error "shield provenance missing before notch trim"}
 set n [$blk findNet $netname]; if {$n eq "NULL"} {error "missing shield net $netname"}
 array set q {};array set objs {};array set owners {};array set lays {};array set ax {};array set eligible {};array set faces {};array set nominal {};array set bins {};array set dirty {}
 array set provenance {};foreach sw $::ot_clock_shield_swires {set provenance($sw) 1}
 set count 0
 foreach sw [$n getSWires] {foreach b [$sw getWires] {
  if {[$b isVia]} {continue};set l [$b getTechLayer];set name [$l getName]
  if {$name ne "M8" && $name ne "M9"} {continue}
  set i $count;incr count;set a [expr {$name eq "M8" ? 1 : 0}]
  set box [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  set q($i) $box;set objs($i) $b;set owners($i) $sw;set lays($i) $l;set ax($i) $a
  set eligible($i) [expr {[info exists provenance($sw)] && [info exists ::ot_clock_shield_outer($b)] && [info exists ::ot_clock_shield_nominal($b)] && [lindex $box [expr {$a+2}]]-[lindex $box $a]==$wdbu}]
  if {$eligible($i)} {set faces($i) $::ot_clock_shield_outer($b);set nominal($i) $::ot_clock_shield_nominal($b)}
  lappend bins($name,[expr {[lindex $box $a]/$gap}]) $i
 }}
 set fixes 0
 for {set i 0} {$i<$count} {incr i} {
  set a $ax($i);set along [expr {1-$a}];set name [$lays($i) getName]
  set edge [lindex $q($i) [expr {$a+2}]];set bin [expr {$edge/$gap}]
  foreach k [list $bin [expr {$bin+1}]] {
   if {![info exists bins($name,$k)]} {continue}
   foreach j $bins($name,$k) {
    if {$i==$j} {continue};set aa $q($i);set bb $q($j)
    set g [expr {[lindex $bb $a]-[lindex $aa [expr {$a+2}]]}]
    if {$g<=0 || $g>=$gap || min([lindex $aa [expr {$along+2}]],[lindex $bb [expr {$along+2}]])<=max([lindex $aa $along],[lindex $bb $along])} {continue}
    set target -1
    if {$eligible($i) && $faces($i)==$a+2} {set target $i;set index [expr {$a+2}];set value [expr {[lindex $aa $index]-($gap-$g)}]} elseif {$eligible($j) && $faces($j)==$a} {set target $j;set index $a;set value [expr {[lindex $bb $index]+($gap-$g)}]}
    if {$target<0} {continue}
    set proposed $q($target);lset proposed $index $value
    set actual [expr {[lindex $proposed [expr {$a+2}]]-[lindex $proposed $a]}]
    if {$actual<$gap || $actual*32<$nominal($target)*31} {continue}
    set q($target) $proposed
    set dirty($target) 1;incr fixes
   }
  }
 }
 foreach i [array names dirty] {
  set axis $ax($i);set actual [expr {[lindex $q($i) [expr {$axis+2}]]-[lindex $q($i) $axis]}]
  puts "OT_SHIELD_WIDTH layer [$lays($i) getName] nominal $nominal($i) actual $actual outer $faces($i) density_multiplier [expr {double($nominal($i))/$actual}]"
  lassign $q($i) x0 y0 x1 y1
  unset -nocomplain ::ot_clock_shield_outer($objs($i)) ::ot_clock_shield_nominal($objs($i))
  odb::dbSBox_destroy $objs($i)
  set b [odb::dbSBox_create $owners($i) $lays($i) $x0 $y0 $x1 $y1 STRIPE]
  set ::ot_clock_shield_outer($b) $faces($i);set ::ot_clock_shield_nominal($b) $nominal($i)
 }
 puts "OT_SHIELD_NOTCH fixes $fixes shapes [array size dirty] min_gap_dbu $gap"
}
ot_trim_shield_notches VSS_SAFE [expr {round(0.64*[$blk getDbUnitsPerMicron])}] [expr {round(0.04*[$blk getDbUnitsPerMicron])}]
set widths {};foreach bb [$ss getWires] {if {![$bb isVia]} {lappend widths [$bb getDX]}}
if {[llength $widths]!=1 || [lindex $widths 0]!=620} {error "face control SAFE failed widths=$widths"}
puts "FACE_CONTROL SAFE PASS width $widths"
set nn [odb::dbNet_create $blk VSS_WRONG]
$nn setSpecial
set ss [odb::dbSWire_create $nn ROUTED]
set ps [odb::dbSWire_create $nn ROUTED]
lappend ::ot_clock_shield_swires $ss
ot_shield_box $ss [$tech findLayer M9] 10000 0 10640 1000 0 640
odb::dbSBox_create $ps [$tech findLayer M9] 10660 -100 11140 1600 STRIPE
proc ot_merge_shields {netname wdbu} { global blk; set n [$blk findNet $netname]; array set g {}; foreach sw [$n getSWires] { foreach b [$sw getWires] { if {[$b isVia]} { continue }; set ly [[$b getTechLayer] getName]; if {$ly ne "M8" && $ly ne "M9"} { continue }; set dx [$b getDX]; set dy [$b getDY]; if {$dy > $dx} { if {$dx != $wdbu} { continue }; lappend g($ly,V,[$b xMin],[$b xMax]) [list [$b yMin] [$b yMax] $b $sw] } else { if {$dy != $wdbu} { continue }; lappend g($ly,H,[$b yMin],[$b yMax]) [list [$b xMin] [$b xMax] $b $sw] } } }; set nin 0; set nout 0; foreach k [array names g] { if {[llength $g($k)] < 2} { continue }; lassign [split $k ,] ly dir c0 c1; set l [[ord::get_db_tech] findLayer $ly]; set runs {}; set cur {}; foreach it [lsort -integer -index 0 $g($k)] { lassign $it lo hi b sw; if {[llength $cur] && $lo <= [lindex $cur 1]} { lset cur 1 [expr {max([lindex $cur 1], $hi)}]; lset cur 2 [concat [lindex $cur 2] [list $b]] } else { if {[llength $cur]} { lappend runs $cur }; set cur [list $lo $hi [list $b] $sw] } }; lappend runs $cur; foreach r $runs { lassign $r lo hi bs sw; if {[llength $bs] < 2} { continue }; incr nin [llength $bs]; incr nout; set face {}; set nominal {}; set safe 1; foreach b $bs { if {![info exists ::ot_clock_shield_outer($b)] || ![info exists ::ot_clock_shield_nominal($b)]} {set safe 0} elseif {$face eq {}} {set face $::ot_clock_shield_outer($b);set nominal $::ot_clock_shield_nominal($b)} elseif {$face ne $::ot_clock_shield_outer($b) || $nominal ne $::ot_clock_shield_nominal($b)} {set safe 0}; unset -nocomplain ::ot_clock_shield_outer($b) ::ot_clock_shield_nominal($b);odb::dbSBox_destroy $b }; if {$dir eq "V"} { set merged [odb::dbSBox_create $sw $l $c0 $lo $c1 $hi STRIPE] } else { set merged [odb::dbSBox_create $sw $l $lo $c0 $hi $c1 STRIPE] }; if {$safe} {set ::ot_clock_shield_outer($merged) $face;set ::ot_clock_shield_nominal($merged) $nominal} } }; puts "OT_SHIELD_MERGE in $nin out $nout" }
ot_merge_shields VSS_WRONG [expr {round(0.64*[[ord::get_db_block] getDbUnitsPerMicron])}]
proc ot_trim_shield_notches {netname wdbu gap} {
 global blk
 if {![info exists ::ot_clock_shield_swires]} {error "shield provenance missing before notch trim"}
 set n [$blk findNet $netname]; if {$n eq "NULL"} {error "missing shield net $netname"}
 array set q {};array set objs {};array set owners {};array set lays {};array set ax {};array set eligible {};array set faces {};array set nominal {};array set bins {};array set dirty {}
 array set provenance {};foreach sw $::ot_clock_shield_swires {set provenance($sw) 1}
 set count 0
 foreach sw [$n getSWires] {foreach b [$sw getWires] {
  if {[$b isVia]} {continue};set l [$b getTechLayer];set name [$l getName]
  if {$name ne "M8" && $name ne "M9"} {continue}
  set i $count;incr count;set a [expr {$name eq "M8" ? 1 : 0}]
  set box [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  set q($i) $box;set objs($i) $b;set owners($i) $sw;set lays($i) $l;set ax($i) $a
  set eligible($i) [expr {[info exists provenance($sw)] && [info exists ::ot_clock_shield_outer($b)] && [info exists ::ot_clock_shield_nominal($b)] && [lindex $box [expr {$a+2}]]-[lindex $box $a]==$wdbu}]
  if {$eligible($i)} {set faces($i) $::ot_clock_shield_outer($b);set nominal($i) $::ot_clock_shield_nominal($b)}
  lappend bins($name,[expr {[lindex $box $a]/$gap}]) $i
 }}
 set fixes 0
 for {set i 0} {$i<$count} {incr i} {
  set a $ax($i);set along [expr {1-$a}];set name [$lays($i) getName]
  set edge [lindex $q($i) [expr {$a+2}]];set bin [expr {$edge/$gap}]
  foreach k [list $bin [expr {$bin+1}]] {
   if {![info exists bins($name,$k)]} {continue}
   foreach j $bins($name,$k) {
    if {$i==$j} {continue};set aa $q($i);set bb $q($j)
    set g [expr {[lindex $bb $a]-[lindex $aa [expr {$a+2}]]}]
    if {$g<=0 || $g>=$gap || min([lindex $aa [expr {$along+2}]],[lindex $bb [expr {$along+2}]])<=max([lindex $aa $along],[lindex $bb $along])} {continue}
    set target -1
    if {$eligible($i) && $faces($i)==$a+2} {set target $i;set index [expr {$a+2}];set value [expr {[lindex $aa $index]-($gap-$g)}]} elseif {$eligible($j) && $faces($j)==$a} {set target $j;set index $a;set value [expr {[lindex $bb $index]+($gap-$g)}]}
    if {$target<0} {continue}
    set proposed $q($target);lset proposed $index $value
    set actual [expr {[lindex $proposed [expr {$a+2}]]-[lindex $proposed $a]}]
    if {$actual<$gap || $actual*32<$nominal($target)*31} {continue}
    set q($target) $proposed
    set dirty($target) 1;incr fixes
   }
  }
 }
 foreach i [array names dirty] {
  set axis $ax($i);set actual [expr {[lindex $q($i) [expr {$axis+2}]]-[lindex $q($i) $axis]}]
  puts "OT_SHIELD_WIDTH layer [$lays($i) getName] nominal $nominal($i) actual $actual outer $faces($i) density_multiplier [expr {double($nominal($i))/$actual}]"
  lassign $q($i) x0 y0 x1 y1
  unset -nocomplain ::ot_clock_shield_outer($objs($i)) ::ot_clock_shield_nominal($objs($i))
  odb::dbSBox_destroy $objs($i)
  set b [odb::dbSBox_create $owners($i) $lays($i) $x0 $y0 $x1 $y1 STRIPE]
  set ::ot_clock_shield_outer($b) $faces($i);set ::ot_clock_shield_nominal($b) $nominal($i)
 }
 puts "OT_SHIELD_NOTCH fixes $fixes shapes [array size dirty] min_gap_dbu $gap"
}
ot_trim_shield_notches VSS_WRONG [expr {round(0.64*[$blk getDbUnitsPerMicron])}] [expr {round(0.04*[$blk getDbUnitsPerMicron])}]
set widths {};foreach bb [$ss getWires] {if {![$bb isVia]} {lappend widths [$bb getDX]}}
if {[llength $widths]!=1 || [lindex $widths 0]!=640} {error "face control WRONG failed widths=$widths"}
puts "FACE_CONTROL WRONG PASS width $widths"
set nn [odb::dbNet_create $blk VSS_DUAL]
$nn setSpecial
set ss [odb::dbSWire_create $nn ROUTED]
set ps [odb::dbSWire_create $nn ROUTED]
lappend ::ot_clock_shield_swires $ss
ot_shield_box $ss [$tech findLayer M9] 20000 0 20640 1000 0 640
ot_shield_box $ss [$tech findLayer M9] 20000 500 20640 1500 2 640
odb::dbSBox_create $ps [$tech findLayer M9] 20660 -100 21140 1600 STRIPE
proc ot_merge_shields {netname wdbu} { global blk; set n [$blk findNet $netname]; array set g {}; foreach sw [$n getSWires] { foreach b [$sw getWires] { if {[$b isVia]} { continue }; set ly [[$b getTechLayer] getName]; if {$ly ne "M8" && $ly ne "M9"} { continue }; set dx [$b getDX]; set dy [$b getDY]; if {$dy > $dx} { if {$dx != $wdbu} { continue }; lappend g($ly,V,[$b xMin],[$b xMax]) [list [$b yMin] [$b yMax] $b $sw] } else { if {$dy != $wdbu} { continue }; lappend g($ly,H,[$b yMin],[$b yMax]) [list [$b xMin] [$b xMax] $b $sw] } } }; set nin 0; set nout 0; foreach k [array names g] { if {[llength $g($k)] < 2} { continue }; lassign [split $k ,] ly dir c0 c1; set l [[ord::get_db_tech] findLayer $ly]; set runs {}; set cur {}; foreach it [lsort -integer -index 0 $g($k)] { lassign $it lo hi b sw; if {[llength $cur] && $lo <= [lindex $cur 1]} { lset cur 1 [expr {max([lindex $cur 1], $hi)}]; lset cur 2 [concat [lindex $cur 2] [list $b]] } else { if {[llength $cur]} { lappend runs $cur }; set cur [list $lo $hi [list $b] $sw] } }; lappend runs $cur; foreach r $runs { lassign $r lo hi bs sw; if {[llength $bs] < 2} { continue }; incr nin [llength $bs]; incr nout; set face {}; set nominal {}; set safe 1; foreach b $bs { if {![info exists ::ot_clock_shield_outer($b)] || ![info exists ::ot_clock_shield_nominal($b)]} {set safe 0} elseif {$face eq {}} {set face $::ot_clock_shield_outer($b);set nominal $::ot_clock_shield_nominal($b)} elseif {$face ne $::ot_clock_shield_outer($b) || $nominal ne $::ot_clock_shield_nominal($b)} {set safe 0}; unset -nocomplain ::ot_clock_shield_outer($b) ::ot_clock_shield_nominal($b);odb::dbSBox_destroy $b }; if {$dir eq "V"} { set merged [odb::dbSBox_create $sw $l $c0 $lo $c1 $hi STRIPE] } else { set merged [odb::dbSBox_create $sw $l $lo $c0 $hi $c1 STRIPE] }; if {$safe} {set ::ot_clock_shield_outer($merged) $face;set ::ot_clock_shield_nominal($merged) $nominal} } }; puts "OT_SHIELD_MERGE in $nin out $nout" }
ot_merge_shields VSS_DUAL [expr {round(0.64*[[ord::get_db_block] getDbUnitsPerMicron])}]
proc ot_trim_shield_notches {netname wdbu gap} {
 global blk
 if {![info exists ::ot_clock_shield_swires]} {error "shield provenance missing before notch trim"}
 set n [$blk findNet $netname]; if {$n eq "NULL"} {error "missing shield net $netname"}
 array set q {};array set objs {};array set owners {};array set lays {};array set ax {};array set eligible {};array set faces {};array set nominal {};array set bins {};array set dirty {}
 array set provenance {};foreach sw $::ot_clock_shield_swires {set provenance($sw) 1}
 set count 0
 foreach sw [$n getSWires] {foreach b [$sw getWires] {
  if {[$b isVia]} {continue};set l [$b getTechLayer];set name [$l getName]
  if {$name ne "M8" && $name ne "M9"} {continue}
  set i $count;incr count;set a [expr {$name eq "M8" ? 1 : 0}]
  set box [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  set q($i) $box;set objs($i) $b;set owners($i) $sw;set lays($i) $l;set ax($i) $a
  set eligible($i) [expr {[info exists provenance($sw)] && [info exists ::ot_clock_shield_outer($b)] && [info exists ::ot_clock_shield_nominal($b)] && [lindex $box [expr {$a+2}]]-[lindex $box $a]==$wdbu}]
  if {$eligible($i)} {set faces($i) $::ot_clock_shield_outer($b);set nominal($i) $::ot_clock_shield_nominal($b)}
  lappend bins($name,[expr {[lindex $box $a]/$gap}]) $i
 }}
 set fixes 0
 for {set i 0} {$i<$count} {incr i} {
  set a $ax($i);set along [expr {1-$a}];set name [$lays($i) getName]
  set edge [lindex $q($i) [expr {$a+2}]];set bin [expr {$edge/$gap}]
  foreach k [list $bin [expr {$bin+1}]] {
   if {![info exists bins($name,$k)]} {continue}
   foreach j $bins($name,$k) {
    if {$i==$j} {continue};set aa $q($i);set bb $q($j)
    set g [expr {[lindex $bb $a]-[lindex $aa [expr {$a+2}]]}]
    if {$g<=0 || $g>=$gap || min([lindex $aa [expr {$along+2}]],[lindex $bb [expr {$along+2}]])<=max([lindex $aa $along],[lindex $bb $along])} {continue}
    set target -1
    if {$eligible($i) && $faces($i)==$a+2} {set target $i;set index [expr {$a+2}];set value [expr {[lindex $aa $index]-($gap-$g)}]} elseif {$eligible($j) && $faces($j)==$a} {set target $j;set index $a;set value [expr {[lindex $bb $index]+($gap-$g)}]}
    if {$target<0} {continue}
    set proposed $q($target);lset proposed $index $value
    set actual [expr {[lindex $proposed [expr {$a+2}]]-[lindex $proposed $a]}]
    if {$actual<$gap || $actual*32<$nominal($target)*31} {continue}
    set q($target) $proposed
    set dirty($target) 1;incr fixes
   }
  }
 }
 foreach i [array names dirty] {
  set axis $ax($i);set actual [expr {[lindex $q($i) [expr {$axis+2}]]-[lindex $q($i) $axis]}]
  puts "OT_SHIELD_WIDTH layer [$lays($i) getName] nominal $nominal($i) actual $actual outer $faces($i) density_multiplier [expr {double($nominal($i))/$actual}]"
  lassign $q($i) x0 y0 x1 y1
  unset -nocomplain ::ot_clock_shield_outer($objs($i)) ::ot_clock_shield_nominal($objs($i))
  odb::dbSBox_destroy $objs($i)
  set b [odb::dbSBox_create $owners($i) $lays($i) $x0 $y0 $x1 $y1 STRIPE]
  set ::ot_clock_shield_outer($b) $faces($i);set ::ot_clock_shield_nominal($b) $nominal($i)
 }
 puts "OT_SHIELD_NOTCH fixes $fixes shapes [array size dirty] min_gap_dbu $gap"
}
ot_trim_shield_notches VSS_DUAL [expr {round(0.64*[$blk getDbUnitsPerMicron])}] [expr {round(0.04*[$blk getDbUnitsPerMicron])}]
set widths {};foreach bb [$ss getWires] {if {![$bb isVia]} {lappend widths [$bb getDX]}}
if {[llength $widths]!=1 || [lindex $widths 0]!=640} {error "face control DUAL failed widths=$widths"}
puts "FACE_CONTROL DUAL PASS width $widths"
set nn [odb::dbNet_create $blk VSS_EXCESS]
$nn setSpecial
set ss [odb::dbSWire_create $nn ROUTED]
set ps [odb::dbSWire_create $nn ROUTED]
lappend ::ot_clock_shield_swires $ss
ot_shield_box $ss [$tech findLayer M9] 30000 0 30160 1000 2 160
odb::dbSBox_create $ps [$tech findLayer M9] 30180 -100 30660 1600 STRIPE
proc ot_merge_shields {netname wdbu} { global blk; set n [$blk findNet $netname]; array set g {}; foreach sw [$n getSWires] { foreach b [$sw getWires] { if {[$b isVia]} { continue }; set ly [[$b getTechLayer] getName]; if {$ly ne "M8" && $ly ne "M9"} { continue }; set dx [$b getDX]; set dy [$b getDY]; if {$dy > $dx} { if {$dx != $wdbu} { continue }; lappend g($ly,V,[$b xMin],[$b xMax]) [list [$b yMin] [$b yMax] $b $sw] } else { if {$dy != $wdbu} { continue }; lappend g($ly,H,[$b yMin],[$b yMax]) [list [$b xMin] [$b xMax] $b $sw] } } }; set nin 0; set nout 0; foreach k [array names g] { if {[llength $g($k)] < 2} { continue }; lassign [split $k ,] ly dir c0 c1; set l [[ord::get_db_tech] findLayer $ly]; set runs {}; set cur {}; foreach it [lsort -integer -index 0 $g($k)] { lassign $it lo hi b sw; if {[llength $cur] && $lo <= [lindex $cur 1]} { lset cur 1 [expr {max([lindex $cur 1], $hi)}]; lset cur 2 [concat [lindex $cur 2] [list $b]] } else { if {[llength $cur]} { lappend runs $cur }; set cur [list $lo $hi [list $b] $sw] } }; lappend runs $cur; foreach r $runs { lassign $r lo hi bs sw; if {[llength $bs] < 2} { continue }; incr nin [llength $bs]; incr nout; set face {}; set nominal {}; set safe 1; foreach b $bs { if {![info exists ::ot_clock_shield_outer($b)] || ![info exists ::ot_clock_shield_nominal($b)]} {set safe 0} elseif {$face eq {}} {set face $::ot_clock_shield_outer($b);set nominal $::ot_clock_shield_nominal($b)} elseif {$face ne $::ot_clock_shield_outer($b) || $nominal ne $::ot_clock_shield_nominal($b)} {set safe 0}; unset -nocomplain ::ot_clock_shield_outer($b) ::ot_clock_shield_nominal($b);odb::dbSBox_destroy $b }; if {$dir eq "V"} { set merged [odb::dbSBox_create $sw $l $c0 $lo $c1 $hi STRIPE] } else { set merged [odb::dbSBox_create $sw $l $lo $c0 $hi $c1 STRIPE] }; if {$safe} {set ::ot_clock_shield_outer($merged) $face;set ::ot_clock_shield_nominal($merged) $nominal} } }; puts "OT_SHIELD_MERGE in $nin out $nout" }
ot_merge_shields VSS_EXCESS [expr {round(0.16*[[ord::get_db_block] getDbUnitsPerMicron])}]
proc ot_trim_shield_notches {netname wdbu gap} {
 global blk
 if {![info exists ::ot_clock_shield_swires]} {error "shield provenance missing before notch trim"}
 set n [$blk findNet $netname]; if {$n eq "NULL"} {error "missing shield net $netname"}
 array set q {};array set objs {};array set owners {};array set lays {};array set ax {};array set eligible {};array set faces {};array set nominal {};array set bins {};array set dirty {}
 array set provenance {};foreach sw $::ot_clock_shield_swires {set provenance($sw) 1}
 set count 0
 foreach sw [$n getSWires] {foreach b [$sw getWires] {
  if {[$b isVia]} {continue};set l [$b getTechLayer];set name [$l getName]
  if {$name ne "M8" && $name ne "M9"} {continue}
  set i $count;incr count;set a [expr {$name eq "M8" ? 1 : 0}]
  set box [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  set q($i) $box;set objs($i) $b;set owners($i) $sw;set lays($i) $l;set ax($i) $a
  set eligible($i) [expr {[info exists provenance($sw)] && [info exists ::ot_clock_shield_outer($b)] && [info exists ::ot_clock_shield_nominal($b)] && [lindex $box [expr {$a+2}]]-[lindex $box $a]==$wdbu}]
  if {$eligible($i)} {set faces($i) $::ot_clock_shield_outer($b);set nominal($i) $::ot_clock_shield_nominal($b)}
  lappend bins($name,[expr {[lindex $box $a]/$gap}]) $i
 }}
 set fixes 0
 for {set i 0} {$i<$count} {incr i} {
  set a $ax($i);set along [expr {1-$a}];set name [$lays($i) getName]
  set edge [lindex $q($i) [expr {$a+2}]];set bin [expr {$edge/$gap}]
  foreach k [list $bin [expr {$bin+1}]] {
   if {![info exists bins($name,$k)]} {continue}
   foreach j $bins($name,$k) {
    if {$i==$j} {continue};set aa $q($i);set bb $q($j)
    set g [expr {[lindex $bb $a]-[lindex $aa [expr {$a+2}]]}]
    if {$g<=0 || $g>=$gap || min([lindex $aa [expr {$along+2}]],[lindex $bb [expr {$along+2}]])<=max([lindex $aa $along],[lindex $bb $along])} {continue}
    set target -1
    if {$eligible($i) && $faces($i)==$a+2} {set target $i;set index [expr {$a+2}];set value [expr {[lindex $aa $index]-($gap-$g)}]} elseif {$eligible($j) && $faces($j)==$a} {set target $j;set index $a;set value [expr {[lindex $bb $index]+($gap-$g)}]}
    if {$target<0} {continue}
    set proposed $q($target);lset proposed $index $value
    set actual [expr {[lindex $proposed [expr {$a+2}]]-[lindex $proposed $a]}]
    if {$actual<$gap || $actual*32<$nominal($target)*31} {continue}
    set q($target) $proposed
    set dirty($target) 1;incr fixes
   }
  }
 }
 foreach i [array names dirty] {
  set axis $ax($i);set actual [expr {[lindex $q($i) [expr {$axis+2}]]-[lindex $q($i) $axis]}]
  puts "OT_SHIELD_WIDTH layer [$lays($i) getName] nominal $nominal($i) actual $actual outer $faces($i) density_multiplier [expr {double($nominal($i))/$actual}]"
  lassign $q($i) x0 y0 x1 y1
  unset -nocomplain ::ot_clock_shield_outer($objs($i)) ::ot_clock_shield_nominal($objs($i))
  odb::dbSBox_destroy $objs($i)
  set b [odb::dbSBox_create $owners($i) $lays($i) $x0 $y0 $x1 $y1 STRIPE]
  set ::ot_clock_shield_outer($b) $faces($i);set ::ot_clock_shield_nominal($b) $nominal($i)
 }
 puts "OT_SHIELD_NOTCH fixes $fixes shapes [array size dirty] min_gap_dbu $gap"
}
ot_trim_shield_notches VSS_EXCESS [expr {round(0.16*[$blk getDbUnitsPerMicron])}] [expr {round(0.04*[$blk getDbUnitsPerMicron])}]
set widths {};foreach bb [$ss getWires] {if {![$bb isVia]} {lappend widths [$bb getDX]}}
if {[llength $widths]!=1 || [lindex $widths 0]!=160} {error "face control EXCESS failed widths=$widths"}
puts "FACE_CONTROL EXCESS PASS width $widths"
puts FACE_CONTROLS_DONE
