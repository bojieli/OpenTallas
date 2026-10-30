# Private exact LN NST cohort. Physical-process only; no RTL, net or port edits.
# Data must be generated from native_candidate.json.gz by prepare_recipe.py.
source /work/ln_postff_data.tcl
proc ln_pf_ff {i} {return [string match DFF* [[$i getMaster] getName]]}
proc ln_pf_context {} {
 set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
 if {$u!=1000} {error "LN_POSTFF wrong native DBU"}
 set r [$b getDieArea]
 if {[$r xMin]!=0 || [$r yMin]!=0 || [$r xMax]!=112320 || [$r yMax]!=112320} {error "LN_POSTFF wrong native outline"}
 set count 0
 foreach i [$b getInsts] {if {[ln_pf_ff $i]} {incr count;if {![dict exists $::ln_pf_ffs [$i getName]]} {error "LN_POSTFF unexpected FF [$i getName]"}}}
 if {$count!=8386 || [dict size $::ln_pf_ffs]!=8386} {error "LN_POSTFF incomplete8386FF cohort"}
 return $b
}
proc ln_pf_check_ffs {homes} {
 set b [ln_pf_context]
 dict for {name row} $::ln_pf_ffs {
  lassign $row master orient x y xx yy clock
  set i [$b findInst $name]
  if {$i eq "NULL" || [[$i getMaster] getName] ne $master} {error "LN_POSTFF native FF master changed $name"}
  set bt [$b findBTerm $clock];set ck [$i findITerm CLK]
  if {$bt eq "NULL" || $ck eq "NULL" || [$ck getNet] ne [$bt getNet]} {error "LN_POSTFF native FF clock changed $name"}
  if {$homes} {
   set box [$i getBBox]
   if {[$i getOrient] ne $orient || [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]] ne [list $x $y $xx $yy]} {error "LN_POSTFF frozen FF home/orientation changed $name"}
  }
 }
}
proc ln_pf_trace {port} {
 set b [ord::get_db_block];set bt [$b findBTerm $port]
 if {$bt eq "NULL" || [$bt getIoType] ne "OUTPUT" || [$bt getSigType] ne "SIGNAL"} {error "LN_POSTFF wrong native output $port"}
 set net [$bt getNet];set seen {};set path {}
 while {$net ne "NULL" && ![dict exists $seen $net]} {
  dict set seen $net 1;set drivers {}
  foreach bt [$net getBTerms] {if {[$bt getIoType] eq "INPUT"} {error "LN_POSTFF output chain aliases input $port"}}
  foreach it [$net getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT" && [$it getSigType] eq "SIGNAL"} {lappend drivers [$it getInst]}}
  if {[llength $drivers]!=1} {error "LN_POSTFF ambiguous native output driver $port"}
  set i [lindex $drivers 0];set name [$i getName]
  if {[ln_pf_ff $i]} {return [list $name $path]}
  if {![regexp {^(BUF|INV)x} [[$i getMaster] getName]]} {error "LN_POSTFF non-pure output chain $port/$name"}
  lappend path $name;set inputs {}
  foreach it [$i getITerms] {if {[[$it getMTerm] getIoType] eq "INPUT" && [$it getSigType] eq "SIGNAL"} {lappend inputs [$it getNet]}}
  if {[llength $inputs]!=1} {error "LN_POSTFF ambiguous pure buffer input $name"}
  set net [lindex $inputs 0]
 }
 error "LN_POSTFF output chain cycle/port $port"
}
proc ln_pf_output_cone {i} {
 set todo {};set seen {};set ports {}
 foreach it [$i getITerms] {if {[[$it getMTerm] getIoType] eq "OUTPUT" && [$it getSigType] eq "SIGNAL"} {lappend todo [$it getNet]}}
 while {[llength $todo]} {
  set n [lindex $todo 0];set todo [lrange $todo 1 end]
  if {$n eq "NULL" || [dict exists $seen $n] || [$n getSigType] eq "CLOCK"} {error "LN_POSTFF invalid post-FF fanout graph"}
  dict set seen $n 1
  foreach bt [$n getBTerms] {if {[$bt getIoType] ne "OUTPUT" || [$bt getSigType] ne "SIGNAL"} {error "LN_POSTFF unrelated port fanout"};lappend ports [$bt getName]}
  foreach it [$n getITerms] {
   if {[[$it getMTerm] getIoType] ne "INPUT" || [$it getSigType] ne "SIGNAL"} continue
   set child [$it getInst]
   if {![regexp {^(BUF|INV)x} [[$child getMaster] getName]]} {error "LN_POSTFF unrelated logic/FF fanout [$child getName]"}
   foreach out [$child getITerms] {if {[[$out getMTerm] getIoType] eq "OUTPUT" && [$out getSigType] eq "SIGNAL"} {lappend todo [$out getNet]}}
  }
 }
 return [lsort -unique $ports]
}
proc ln_pf_validate_targets {} {
 set b [ord::get_db_block]
 dict for {name row} $::ln_pf_targets {
  lassign $row master orient x y xx yy group owners
  set i [$b findInst $name]
  if {$i eq "NULL" || [[$i getMaster] getName] ne $master || ![regexp {^(BUF|INV)x} $master]} {error "LN_POSTFF changed selected pure buffer $name"}
  if {[[$i getMaster] getWidth]!=$xx-$x || [[$i getMaster] getHeight]!=$yy-$y} {error "LN_POSTFF changed target footprint $name"}
  foreach it [$i getITerms] {if {[$it getNet] ne "NULL" && [[$it getNet] getSigType] eq "CLOCK"} {error "LN_POSTFF selected cell is on a clock $name"}}
  set expected_ports {}
  foreach owner $owners {
   lassign $owner ff port;lappend expected_ports $port;lassign [ln_pf_trace $port] actual path
   if {$actual ne $ff || [lsearch -exact $path $name]<0} {error "LN_POSTFF changed native post-FF ownership $name/$port"}
  }
  if {[ln_pf_output_cone $i] ne [lsort -unique $expected_ports]} {error "LN_POSTFF changed complete output fanout $name"}
  if {$group ne "" && [$b findGroup $group] eq "NULL"} {error "LN_POSTFF missing existing physical home group $group"}
 }
}
proc ln_pf_obstacle {rect bucketsName} {
 upvar 1 $bucketsName buckets
 lassign $rect x y xx yy
 for {set row [expr {int(floor($y/270.0))}]} {$row*270<$yy} {incr row} {dict lappend buckets $row $rect}
}
proc ln_pf_sites {verify} {
 set b [ord::get_db_block];set rows {};set buckets {}
 foreach r [$b getRows] {set box [$r getBBox];set s [$r getSite];dict lappend rows [$box yMin] [list [$box xMin] [$box xMax] [$s getWidth] [$s getHeight] [$r getOrient]]}
 foreach i [$b getInsts] {
  set name [$i getName]
  if {[dict exists $::ln_pf_targets $name] || (!$verify && [ln_pf_ff $i])} continue
  if {[$i getPlacementStatus] in {NONE UNPLACED}} continue
  # PREPARE permits GPL to move ordinary logic. FFs use their exact reviewed homes below.
  if {!$verify && [$i getPlacementStatus] ni {FIRM LOCKED COVER} && ![string match *TAP* [[$i getMaster] getName]] && ![[$i getMaster] isBlock]} continue
  set r [$i getBBox];ln_pf_obstacle [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] buckets
 }
 if {!$verify} {dict for {name row} $::ln_pf_ffs {ln_pf_obstacle [lrange $row 2 5] buckets}}
 foreach block [$b getBlockages] {
  if {[$block isSoft] || [$block getMaxDensity]>0} continue
  set r [$block getBBox];ln_pf_obstacle [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] buckets
 }
 dict for {name row} $::ln_pf_targets {
  lassign $row master orient x y xx yy group owners;set legal 0
  if {[dict exists $rows $y]} {foreach r [dict get $rows $y] {lassign $r a c sw h o;if {$x>=$a && $xx<=$c && ($x-$a)%$sw==0 && $yy-$y==$h && $o eq $orient} {set legal 1;break}}}
  if {!$legal || $x<4320 || $y<4320 || $xx>108000 || $yy>108000} {error "LN_POSTFF target is not an actual legal core row/site $name"}
  set r [expr {int(floor($y/270.0))}]
  if {[dict exists $buckets $r]} {foreach rect [dict get $buckets $r] {lassign $rect a z c d;if {$x<$c && $a<$xx && $y<$d && $z<$yy} {error "LN_POSTFF occupied target $name"}}}
  ln_pf_obstacle [list $x $y $xx $yy] buckets
 }
}
proc ln_postff_prepare {} {
 # All identities/clocks/chains/sites validate before any placement changes.
 ln_pf_check_ffs 0;ln_pf_validate_targets;ln_pf_sites 0
 set b [ord::get_db_block]
 dict for {name row} $::ln_pf_ffs {
  lassign $row master orient x y xx yy clock;set i [$b findInst $name]
  $i setPlacementStatus PLACED;$i setOrient $orient;$i setLocation $x $y;$i setPlacementStatus FIRM
 }
 dict for {name row} $::ln_pf_targets {
  lassign $row master orient x y xx yy group owners;set i [$b findInst $name]
  set old [$i getGroup]
  if {$old ne "NULL"} {$old removeInst $i}
  if {$group ne ""} {[$b findGroup $group] addInst $i}
  $i setPlacementStatus PLACED;$i setOrient $orient;$i setLocation $x $y;$i setPlacementStatus FIRM
 }
 ln_pf_check_ffs 1
 puts "LN_POSTFF_PREPARED existing_BUF_INV=[dict size $::ln_pf_targets] existing_FF=8386 clock_port_RTL_cycles_unchanged"
}
proc ln_postff_verify {} {
 ln_pf_check_ffs 1;ln_pf_validate_targets;ln_pf_sites 1
 set b [ord::get_db_block]
 dict for {name row} $::ln_pf_targets {
  lassign $row master orient x y xx yy group owners;set i [$b findInst $name];set r [$i getBBox]
  if {[$i getOrient] ne $orient || [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]] ne [list $x $y $xx $yy]} {error "LN_POSTFF target moved after G1 $name"}
  set g [$i getGroup];set actual [expr {$g eq "NULL" ? "" : [$g getName]}]
  if {$actual ne $group} {error "LN_POSTFF target physical home changed $name"}
 }
 puts "LN_POSTFF_G1_GUARD_PASS all8386FFmasters_homes_orients_clocks_and109postFFsites_exact"
}
