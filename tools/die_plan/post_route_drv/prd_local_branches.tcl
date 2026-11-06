# Explicit measured driver-chain locality. Default OFF; no clock/FF/netlist change.
if {![llength [info commands ot_prd_net_key]]} {source [file join [file dirname [info script]] prd_targeted.tcl]}
proc ot_prd_local_free {b x y master} {
 set c [$b getCoreArea];set w [$master getWidth];set h [$master getHeight]
 if {$x<[$c xMin] || $y<[$c yMin] || $x+$w>[$c xMax] || $y+$h>[$c yMax]} {return 0}
 foreach r $::ot_prd_local_macros {
  lassign $r a bb cc d
  if {$x<$cc && $a<$x+$w && $y<$d && $bb<$y+$h} {return 0}
 }
 return 1
}
proc ot_prd_local_site {b x y master} {
 set u [[ord::get_db_tech] getDbUnitsPerMicron];set step [expr {round(2.16*$u)}]
 for {set rad 0} {$rad<=24} {incr rad} {
  for {set dx [expr {-$rad}]} {$dx<=$rad} {incr dx} {
   foreach dy [lsort -unique [list [expr {$rad-abs($dx)}] [expr {abs($dx)-$rad}]]] {
    set xx [expr {round($x)+$dx*$step}];set yy [expr {round($y)+$dy*$step}]
    if {[ot_prd_local_free $b $xx $yy $master]} {return [list $xx $yy]}
   }
  }
 }
 error "OT_PRD_LOCAL_BRANCH no macro-free nearby site"
}
proc ot_prd_local_branches {file} {
 set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
 set ::ot_prd_local_macros {};set halo 0
 if {[info exists ::env(OT_PRD_LOCAL_MACRO_HALO_UM)]} {
  set value $::env(OT_PRD_LOCAL_MACRO_HALO_UM)
  if {![string is double -strict $value] || $value<=0} {error "OT_PRD_LOCAL_BRANCH invalid explicit macro halo"}
  set halo [expr {round($value*$u)}]
 }
 foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  if {!$halo} {error "OT_PRD_LOCAL_BRANCH macro-bearing use requires explicit site-authorized OT_PRD_LOCAL_MACRO_HALO_UM"}
  set r [$i getBBox];lappend ::ot_prd_local_macros [list [expr {[$r xMin]-$halo}] [expr {[$r yMin]-$halo}] [expr {[$r xMax]+$halo}] [expr {[$r yMax]+$halo}]]
 }
 set ::ot_prd_local_targets {};set plans {};set used {};set expected 0
 set f [open $file r];set text [read $f];close $f
 foreach line [split $text \n] {
  if {$line eq ""} continue
  incr expected
  lassign [split $line \t] name master input output
  set i [$b findInst $name]
  if {$i eq "NULL" || [[$i getMaster] getName] ne $master || ![string match BUF* $master] || [$i getPlacementStatus] in {FIRM LOCKED COVER} || [$i isDoNotTouch]} {error "OT_PRD_LOCAL_BRANCH stale/protected driver $name"}
  if {[[[$i findITerm A] getNet] getName] ne $input || [[[$i findITerm Y] getNet] getName] ne $output} {error "OT_PRD_LOCAL_BRANCH graph differs $name"}
  set net [[$i findITerm Y] getNet]
  if {[$net getSigType] ne "SIGNAL" || [$net isDoNotTouch]} {error "OT_PRD_LOCAL_BRANCH protected output $output"}
  dict set ::ot_prd_local_targets [ot_prd_net_key $output] 1
  set xx {};set yy {}
  foreach t [$net getITerms] {
   if {[[$t getMTerm] getIoType] ne "INPUT"} continue
   lassign [[$t getInst] getLocation] x y;lappend xx $x;lappend yy $y
  }
  if {![llength $xx]} {error "OT_PRD_LOCAL_BRANCH no sinks $name"}
  set tx [expr {([tcl::mathfunc::min {*}$xx]+[tcl::mathfunc::max {*}$xx])/2.0}]
  set ty [expr {([tcl::mathfunc::min {*}$yy]+[tcl::mathfunc::max {*}$yy])/2.0}]
  set chain [list $i];set cur $i;set seen {}
  while {1} {
   set n [[$cur findITerm A] getNet];set drv {};set loads 0
   foreach t [$n getITerms] {
    if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend drv [$t getInst]}
    if {[[$t getMTerm] getIoType] eq "INPUT"} {incr loads}
   }
   if {[llength $drv]!=1} {
    if {[llength [$n getBTerms]]!=1} {error "OT_PRD_LOCAL_BRANCH no unique anchor $name"}
    set q [[lindex [$n getBTerms] 0] getBBox];set ax [expr {([$q xMin]+[$q xMax])/2.0}];set ay [expr {([$q yMin]+[$q yMax])/2.0}];break
   }
   set up [lindex $drv 0]
   if {[dict exists $seen [$up getName]]} {error "OT_PRD_LOCAL_BRANCH cycle"};dict set seen [$up getName] 1
   if {$loads!=1 || ![string match BUF* [[$up getMaster] getName]] || [$up getPlacementStatus] in {FIRM LOCKED COVER} || [$up isDoNotTouch]} {
    lassign [$up getLocation] ax ay;break
   }
   lappend chain $up;set cur $up
  }
  set chain [lreverse $chain];set count [llength $chain];set k 0
  foreach cell $chain {
   incr k;set nm [$cell getName]
   set x [expr {$ax+($tx-$ax)*$k/($count+1)}];set y [expr {$ay+($ty-$ay)*$k/($count+1)}]
   set xy [ot_prd_local_site $b $x $y [$cell getMaster]]
   if {[dict exists $used $nm] && [dict get $used $nm] ne $xy} {error "OT_PRD_LOCAL_BRANCH shared chain cell $nm"}
   dict set used $nm $xy
  }
 }
 if {!$expected || [dict size $::ot_prd_local_targets]!=$expected} {error "OT_PRD_LOCAL_BRANCH empty/duplicate donor driver nets"}
 set f [open [file join $::env(RESULTS_DIR) prd_local_branches.tsv] w]
 dict for {name xy} $used {
  set i [$b findInst $name];lassign [$i getLocation] ox oy;lassign $xy x y
  puts $f "$name\t[expr {$ox/double($u)}]\t[expr {$oy/double($u)}]\t[expr {$x/double($u)}]\t[expr {$y/double($u)}]"
  if {![info exists ::env(OT_PRD_LOCAL_BRANCH_PLAN_ONLY)] || $::env(OT_PRD_LOCAL_BRANCH_PLAN_ONLY) ne "1"} {$i setLocation $x $y}
 }
 close $f
 puts "OT_PRD_LOCAL_BRANCH targets [dict size $::ot_prd_local_targets] movable_chain_buffers [dict size $used] hardmacros[llength $::ot_prd_local_macros] explicit_macro_halo_dbu$halo netlist_and_clocks_unchanged"
}

proc ot_prd_local_hold_sequential {} {
 set ::ot_prd_local_sequential {}
 foreach i [[ord::get_db_block] getInsts] {
  set seq 0
  foreach t [[$i getMaster] getMTerms] {if {[$t getSigType] eq "CLOCK"} {set seq 1;break}}
  # ASAP7 liberty clock pins are also guarded by the characterized master class.
  if {[regexp {^(DFF|SDFF)} [[$i getMaster] getName]]} {set seq 1}
  if {!$seq || [[$i getMaster] isBlock]} continue
  dict set ::ot_prd_local_sequential [$i getName] [list [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch]]
  $i setPlacementStatus FIRM
  $i setDoNotTouch 1
 }
 puts "OT_PRD_LOCAL_BRANCH sequential poses held [dict size $::ot_prd_local_sequential]"
}
proc ot_prd_local_sequential_audit {} {
 set b [ord::get_db_block]
 dict for {n old} $::ot_prd_local_sequential {
  set i [$b findInst $n]
  if {$i eq "NULL" || [list [[$i getMaster] getName] [$i getLocation] [$i getOrient]] ne [lrange $old 0 2]} {error "OT_PRD_LOCAL_BRANCH sequential pose/master changed: $n"}
  $i setPlacementStatus [lindex $old 3];$i setDoNotTouch [lindex $old 4]
 }
 puts "OT_PRD_LOCAL_BRANCH sequential audit PASS [dict size $::ot_prd_local_sequential]"
}
if {[info exists ::env(OT_PRD_LOCAL_BRANCHES)] && $::env(OT_PRD_LOCAL_BRANCHES) ne ""} {ot_prd_local_branches $::env(OT_PRD_LOCAL_BRANCHES); ot_prd_local_hold_sequential}
