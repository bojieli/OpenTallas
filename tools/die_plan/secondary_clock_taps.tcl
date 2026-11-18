# Explicit existing-source density tree; no ports, clocks, periods or exceptions are created.
# Canonical core_density_taps owns clustering/F4/macro-interface assignment.
if {![info exists ::ot_secondary_clock_spec]} { return }
namespace eval ::ot_secondary_clock {}
proc ::ot_secondary_clock::ordinary_roots {blk selected} {
 set out {}
 foreach clock [all_clocks] {
  foreach source [get_property $clock sources] {
   set name [get_full_name $source];set bt [$blk findBTerm $name]
   if {$bt eq "NULL" || [$bt getIoType] ne "INPUT" || $name eq $selected} continue
   set net [$bt getNet];set terms {}
   foreach it [$net getITerms] {lappend terms [list [[$it getInst] getName] [[$it getMTerm] getName]]}
   dict set out $name [list [$net getName] [lsort $terms]]
  }
 }
 return $out
}
proc ::ot_secondary_clock::apply {spec} {
 if {[info exists ::ot_secondary_clock_active]} {error "SECONDARY_CLOCK repeated installation"}
 foreach key {port clock target dmax_um radius_um} {if {![dict exists $spec $key]} {error "SECONDARY_CLOCK missing $key"}}
 set blk [ord::get_db_block];set port [dict get $spec port];set clock [dict get $spec clock]
 set bt [$blk findBTerm $port]
 if {$bt eq "NULL" || [$bt getIoType] ne "INPUT" || [$bt getNet] eq "NULL"} {error "SECONDARY_CLOCK requires an existing input root $port"}
 set sources {}
 foreach c [all_clocks] {foreach p [get_property $c sources] {if {[get_full_name $p] eq $port} {lappend sources [get_full_name $c]}}}
 if {[lsort -unique $sources] ne [list $clock]} {error "SECONDARY_CLOCK native timing source mismatch $port: $sources"}
 set root [$bt getNet];set pins {}
 foreach it [$root getITerms] {if {[$it isInputSignal]} {lappend pins $it}}
 if {![llength $pins]} {error "SECONDARY_CLOCK source has no direct native sinks"}
 set before [ordinary_roots $blk $port];set states {};set frozen {}
 foreach inst [$blk getInsts] {
  if {[$inst getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} continue
  set name [$inst getName];dict set states $name [list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]]
  if {[$inst getPlacementStatus] eq "PLACED"} {$inst setPlacementStatus FIRM;lappend frozen $name}
 }
 set overrides [dict create OT_DTAP_PORT $port OT_DTAP_CELL BUFx24_ASAP7_75t_R OT_DTAP_LAYOUT density OT_DTAP_ID_OFFSET 900000 OT_DTAP_TARGET [dict get $spec target] OT_DTAP_DMAX_UM [dict get $spec dmax_um] OT_DTAP_BOUNDED_F4 1 OT_DTAP_OUTLIER_LEAVES 1 OT_DTAP_SITES {} OT_DTAP_ATOMIC_GROUPS {}]
 set saved {}
 dict for {key value} $overrides {
  dict set saved $key [list [info exists ::env($key)] [expr {[info exists ::env($key)] ? $::env($key) : ""}]]
  set ::env($key) $value
 }
 try {
  uplevel #0 [list source [file join [file dirname [info script]] core_density_taps.tcl]]
 } finally {
  dict for {key item} $saved {if {[lindex $item 0]} {set ::env($key) [lindex $item 1]} else {unset ::env($key)}}
  foreach name $frozen {[$blk findInst $name] setPlacementStatus PLACED}
 }
 dict for {name state} $states {
  set inst [$blk findInst $name]
  if {[list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]] ne $state} {error "SECONDARY_CLOCK moved an existing instance $name"}
 }
 if {[ordinary_roots $blk $port] ne $before} {error "SECONDARY_CLOCK changed an ordinary source"}
 if {[$bt getNet] ne $root} {error "SECONDARY_CLOCK native source disconnected"}
 set leafnets {};set max_radius 0.;set u [$blk getDbUnitsPerMicron];set max_load 0;set count 0
 foreach row $::dt_taps {
  set id [lindex $row 0];set net [lindex $row 3]
  set inst [$blk findInst ot_dtap_[expr {900000+$id}]];set bb [$inst getBBox]
  set x [expr {([$bb xMin]+[$bb xMax])/2.}];set y [expr {([$bb yMin]+[$bb yMax])/2.}]
  set load 0
  foreach it [$net getITerms] {
   if {![$it isInputSignal]} continue
   if {![[[$it getInst] getMaster] isBlock]} {incr load}
   set b [$it getBBox]
   set d [expr {(abs(([$b xMin]+[$b xMax])/2.-$x)+abs(([$b yMin]+[$b yMax])/2.-$y))/$u}]
   set max_radius [expr {max($max_radius,$d)}]
  }
  if {$load>[dict get $spec target]} {error "SECONDARY_CLOCK leaf $id overloaded $load"}
  set max_load [expr {max($max_load,$load)}];dict set leafnets $net 1
 }
 foreach it $pins {if {![dict exists $leafnets [$it getNet]]} {error "SECONDARY_CLOCK native sink not assigned exactly once"};incr count}
 if {$max_radius>[dict get $spec radius_um]} {puts "SECONDARY_CLOCK INFO radius $max_radius exceeds declared local bound (LIMIT-BIND-1: not blocking)"}
 if {[file exists /work/pg_connect.tcl]} {uplevel #0 {source /work/pg_connect.tcl};ot_pg_connect_all secondary_density;ot_pg_require_bound secondary_density}
 set ::ot_secondary_clock_active 1
 puts "SECONDARY_CLOCK_APPLIED port={$port} clock=$clock driver=[$::dt_master getName] sinks=$count leaves=[dict size $leafnets] max_std_load=$max_load max_radius_um=$max_radius added_cycles=0 ordinary_sources_unchanged=1 placements_unchanged=1"
}
::ot_secondary_clock::apply $::ot_secondary_clock_spec
