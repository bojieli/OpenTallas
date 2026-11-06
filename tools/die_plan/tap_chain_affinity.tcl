# Default-off pre-CTS affinity for individual bits of generated delay chains.
# Captures only genuine register clock pins on the original direct input clock.
# It never follows gates/muxes/inverters, changes data/reset, or moves hard clocks.
namespace eval ::ot_tap_chain {
 variable original {};variable load {};variable radius 0;variable cap 0
 variable moved 0;variable joined 0;variable segments 0;variable already 0;variable trace {};variable dbu 1
 proc identity {name} {
  set name [string map {\\ {}} $name]
  if {[regexp {^(.*(?:u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_).+[/.]r)\[([0-9]+)\]\[([0-9]+)\]\$_DFF_P} $name -> prefix stage bit]} {
   return [list $prefix $stage $bit]
  }
  if {[regexp {^(.*(?:u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_).+[/.]r)\[([0-9]+)\]\$_DFF_P} $name -> prefix stage]} {
   return [list $prefix $stage scalar]
  }
  if {[regexp {^(.*(?:u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_).+[/.])q\[([0-9]+)\]\$_DFF_P} $name -> prefix bit]} {
   return [list ${prefix}r terminal $bit]
  }
  if {[regexp {^(.*(?:u_d[0-9]+_|u_lpad_|u_r8b_strap_|u_pd[0-9]+_).+[/.])q\$_DFF_P} $name -> prefix]} {
   return [list ${prefix}r terminal scalar]
  }
  return {}
 }
 proc direct {net} {
  foreach it [$net getITerms] {
   if {[$it isOutputSignal]} {error "OT_TAP_CHAIN source [$net getName] has a cell driver"}
  }
 }
 proc capture {root} {
  variable original;set original {};direct $root
  foreach p [all_registers -clock_pins] {
   set it [sta::sta_to_db_pin $p]
   if {$it eq "NULL" || $it eq "" || [$it getNet] ne $root} {continue}
   set inst [$it getInst];set master [$inst getMaster]
   if {[$master isBlock] || [identity [$inst getName]] eq {}} {continue}
   dict set original $it [list [$root getName] [$master getName] [$inst getName]]
  }
  puts "OT_TAP_CHAIN eligible original-source clock pins [dict size $original]"
 }
 proc target {members} {
  global ct_taps
  variable load;variable cap;variable radius
  set best {};set cost 0
  foreach tp $ct_taps {
   set net [lindex $tp 1];set add 0;set dsum 0;set good 1
   foreach row $members {
    lassign $row stage it x y
    set d [expr {abs($x-[lindex $tp 2])+abs($y-[lindex $tp 3])}]
    if {$d>$radius} {set good 0;break}
    set dsum [expr {$dsum+$d}]
    if {[$it getNet] ne $net} {incr add}
   }
   if {!$good || [dict get $load [$net getName]]+$add>$cap} {continue}
   if {$best eq {} || $dsum<$cost} {set best $tp;set cost $dsum}
  }
  return $best
 }
 proc join {members} {
  variable load;variable moved;variable joined;variable segments;variable already;variable trace;variable dbu;variable original
  if {[llength $members]<2} {return}
  set same 1;set first [[lindex [lindex $members 0] 1] getNet]
  foreach row $members {if {[[lindex $row 1] getNet] ne $first} {set same 0;break}}
  if {$same} {incr already;return}
  set tp [target $members];if {$tp eq {}} {return}
  set dst [lindex $tp 1];set n 0
  foreach row $members {
   set it [lindex $row 1];set old [$it getNet]
   if {$old eq $dst} {continue}
   set oldname [$old getName];$it disconnect;$it connect $dst
   dict incr load $oldname -1;dict incr load [$dst getName] 1;incr n
  }
  incr segments;if {$n} {incr joined;incr moved $n}
  if {$trace ne {}} {
   foreach row $members {
    lassign $row stage it x y;set inst [$it getInst]
    puts $trace "$segments\t[lindex $tp 0]\t$stage\t[$inst getName]\t[[$it getMTerm] getName]\t[lindex [dict get $original $it] 0]\t[expr {$x/double($dbu)}]\t[expr {$y/double($dbu)}]"
   }
  }
 }
 proc apply {} {
  global ct_taps
  variable original;variable load;variable radius;variable cap
  variable moved;variable joined;variable segments;variable already;variable trace;variable dbu
  set radius_um [expr {[info exists ::env(OT_TAP_CHAIN_RADIUS_UM)] ? $::env(OT_TAP_CHAIN_RADIUS_UM) : 200.0}]
  set limit [expr {[info exists ::env(OT_TAP_CHAIN_MAX_GROUP)] ? $::env(OT_TAP_CHAIN_MAX_GROUP) : 24}]
  set cap [expr {[info exists ::env(OT_TAP_MAX_SINKS)] ? $::env(OT_TAP_MAX_SINKS) : 1200}]
  if {$radius_um<=0 || $limit<2 || $limit>$cap || $cap<1} {error "OT_TAP_CHAIN invalid radius/group/capacity"}
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set radius [expr {$radius_um*$dbu}]
  set load {};set taps {};set groups {};set moved 0;set joined 0;set segments 0;set already 0;set trace {}
  if {[info exists ::env(RESULTS_DIR)]} {
   set trace [open [file join $::env(RESULTS_DIR) ot_tap_chain_groups.tsv] w]
   puts $trace "group\ttap\tstage\tinstance\tclock_pin\toriginal_source\tx_um\ty_um"
  }
  foreach tp $ct_taps {
   set net [lindex $tp 1];direct $net;set n 0
   foreach it [$net getITerms] {if {[$it isInputSignal]} {incr n}}
   dict set load [$net getName] $n;dict set taps [$net getName] 1
  }
  dict for {it source} $original {
   set inst [$it getInst];set master [$inst getMaster]
   if {[$master isBlock] || [$master getName] ne [lindex $source 1]} {error "OT_TAP_CHAIN eligible register master changed"}
   if {[$inst getName] ne [lindex $source 2]} {error "OT_TAP_CHAIN eligible register identity changed"}
   set net [$it getNet]
   if {![dict exists $taps [$net getName]]} {error "OT_TAP_CHAIN eligible pin left its declared source family"}
   lassign [identity [$inst getName]] prefix stage bit
   if {$prefix eq {}} {error "OT_TAP_CHAIN eligible register identity changed"}
   lassign [$inst getLocation] x y
   dict lappend groups "[lindex $source 0]:$prefix:$bit" [list $stage $it $x $y]
  }
  foreach key [lsort [dict keys $groups]] {
   set rows {};set terminals {};set top -1
   foreach row [dict get $groups $key] {
    if {[lindex $row 0] eq "terminal"} {lappend terminals $row;continue}
    set top [expr {max($top,[lindex $row 0])}];lappend rows $row
   }
   # A terminal is included only beside its actually captured preceding stages.
   if {$top>=0 && [llength $terminals]==1} {lappend rows [lreplace [lindex $terminals 0] 0 0 [expr {$top+1}]]}
   set rows [lsort -integer -index 0 $rows];set segment {};set prev -2
   foreach row $rows {
    set stage [lindex $row 0];set trial [concat $segment [list $row]]
    if {[llength $segment] && ($stage!=$prev+1 || [llength $trial]>$limit || [target $trial] eq {})} {join $segment;set segment {}}
    lappend segment $row;set prev $stage
   }
   join $segment
  }
  if {$trace ne {}} {close $trace;set trace {}}
  puts "OT_TAP_CHAIN groups [dict size $groups] segments $segments joined $joined moved $moved already $already radius_um $radius_um max_group $limit capacity $cap"
 }
}
