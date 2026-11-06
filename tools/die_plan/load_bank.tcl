# Exact-cell, same-cycle local banks. Source after face_flops.tcl.
# API: lb_begin block whitelistFF maxCells; lb_bank net {{inst pin} ...} x y
# Coordinates are DBU. Copies remain movable; caller owns placement policy.
namespace eval lb { variable serial 0; variable audit {}; variable created {} }
# ORFS can source hooks inside a procedure; face_flops publishes ff_blk globally.
# Use one explicit global scope for the caller's bank declarations as well.
proc lb_apply {path} {
 return [uplevel #0 [list source $path]]
}
proc lb_begin {block ff_names {limit 64}} {
 set ::lb::block $block; set ::lb::limit $limit; set ::lb::allow [dict create]
 foreach n $ff_names {dict set ::lb::allow $n 1}
 set ::lb::audit {}; set ::lb::created {}
}
proc lb_isff {i} {expr {[string first DFF [[$i getMaster] getName]] >= 0}}
proc lb_boundary_input {i} {
 set d [$i findITerm D]
 if {$d eq "NULL"} {return 1}
 set n [$d getNet]; set seen {}
 for {set k 0} {$k < 32} {incr k} {
  if {$n eq "NULL" || [dict exists $seen $n]} {return 1}; dict set seen $n 1
  if {[llength [$n getBTerms]]} {return 1}
  set ds {}; foreach t [$n getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend ds $t}}
  if {[llength $ds] != 1} {return 1}
  set u [[lindex $ds 0] getInst]; set m [[$u getMaster] getName]
  if {![string match BUF* $m] && ![string match INV* $m]} {return 0}
  set ins {}; foreach t [$u getITerms] {if {[[$t getMTerm] getIoType] eq "INPUT"} {lappend ins $t}}
  if {[llength $ins] != 1} {return 1}; set n [[lindex $ins 0] getNet]
 }
 return 1
}
proc lb_copy_net {net depth} {
 if {[dict exists $::lb::memo $net]} {return [dict get $::lb::memo $net]}
 if {$depth > 32} {error "LOAD_BANK cone depth exceeded"}
 # Any primary connection is an explicit frontier; no clock/port clones.
 if {[llength [$net getBTerms]]} {return $net}
 set ds {}; foreach t [$net getITerms] {if {[[$t getMTerm] getIoType] eq "OUTPUT"} {lappend ds $t}}
 if {[llength $ds] != 1} {error "LOAD_BANK requires one driver: [$net getName]"}
 set dt [lindex $ds 0]; set src [$dt getInst]; set ff [lb_isff $src]
 if {[string match BLOCK* [[$src getMaster] getType]]} {error "LOAD_BANK refuses hard macro frontier [$src getName]"}
 if {$ff && ![dict exists $::lb::allow [$src getName]]} {return $net}
 if {$ff && [lb_boundary_input $src]} {error "LOAD_BANK refuses primary-input capture FF [$src getName]"}
 if {[dict exists $::lb::instances $src]} {
  set c [dict get $::lb::instances $src]
  return [[$c findITerm [[$dt getMTerm] getName]] getNet]
 }
 incr ::lb::count
 if {$::lb::count > $::lb::limit} {error "LOAD_BANK cell budget exceeded"}
 incr ::lb::serial
 set c [odb::dbInst_create $::lb::block [$src getMaster] "ot_loadbank_$::lb::serial"]
 dict set ::lb::instances $src $c
 # Memoize all outputs before visiting inputs; combinational cycles still fail check below.
 foreach t [$src getITerms] {
  set mt [$t getMTerm]; set old [$t getNet]
  if {[$mt getIoType] ne "OUTPUT" || $old eq "NULL"} continue
  set nn [odb::dbNet_create $::lb::block "ot_loadbank_$::lb::serial\_[$mt getName]"]
  [$c findITerm [$mt getName]] connect $nn; dict set ::lb::memo $old $nn
 }
 foreach t [$src getITerms] {
  set mt [$t getMTerm]; set old [$t getNet]
  if {[$mt getIoType] ne "INPUT" || [$mt getSigType] in {POWER GROUND} || $old eq "NULL"} continue
  # FF D/en/reset/clock stay EXACTLY on original nets, including feedback.
  if {$ff} {set nn $old} else {set nn [lb_copy_net $old [expr {$depth+1}]]}
  [$c findITerm [$mt getName]] connect $nn
  lappend ::lb::audit [list $src $c [$mt getName] $old $nn $ff]
 }
 $c setLocation $::lb::x $::lb::y; $c setPlacementStatus PLACED
 lappend ::lb::created $c
 return [dict get $::lb::memo $net]
}
proc lb_bank {net loads x y} {
 set ::lb::memo {}; set ::lb::instances {}; set ::lb::count 0
 set ::lb::x $x; set ::lb::y $y
 # Validate the whole request before changing any load.
 set its {}
 foreach item $loads {
  lassign $item name pin; set i [$::lb::block findInst $name]
  if {$i eq "NULL"} {error "LOAD_BANK missing load $name"}
  set t [$i findITerm $pin]
  if {$t eq "NULL" || [$t getNet] ne $net || [[$t getMTerm] getIoType] ne "INPUT"} {error "LOAD_BANK mismatched load $name/$pin"}
  lappend its $t
 }
 if {![llength $its]} {error "LOAD_BANK empty bank"}
 set nn [lb_copy_net $net 0]
 if {$nn eq $net} {error "LOAD_BANK request stopped at frontier"}
 foreach t $its {$t disconnect; $t connect $nn}
 lb_audit
 return $::lb::created
}
proc lb_audit {} {
 foreach row $::lb::audit {
  lassign $row src copy pin old expected ff
  if {[[$src getMaster] getName] ne [[$copy getMaster] getName]} {error "LOAD_BANK master mismatch"}
  if {[[$src findITerm $pin] getNet] ne $old || [[$copy findITerm $pin] getNet] ne $expected} {error "LOAD_BANK input mismatch"}
  if {$ff && $old ne $expected} {error "LOAD_BANK FF phase/input mismatch"}
 }
 return [llength $::lb::audit]
}
