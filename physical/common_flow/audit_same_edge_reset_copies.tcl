# Check persisted same-state copies after CTS/repair without blocking CLK/D ECOs.
namespace eval ot_lpc_audit {variable block [ord::get_db_block]}
proc ot_lpc_audit::null {x} {expr {$x eq "NULL" || $x eq ""}}
proc ot_lpc_audit::root_name {name} {
 set seen {}
 while {[dict exists $::ot_lpc_audit_alias $name]} {
  if {[dict exists $seen $name]} {error "RESET_COPY_AUDIT aliascycle"}
  dict set seen $name 1;set name [dict get $::ot_lpc_audit_alias $name]
 }
 return $name
}
proc ot_lpc_audit::signature {net {seen {}}} {
 if {[null $net]} {return {unconnected}}
 if {[dict exists $seen $net]} {error "RESET_COPY_AUDIT bufferloop"}
 dict set seen $net 1
 if {[$net getSigType] eq "GROUND"} {return {constant 0}}
 if {[$net getSigType] eq "POWER"} {return {constant 1}}
 set drivers {}
 foreach bt [$net getBTerms] {if {[$bt getIoType] eq "INPUT"} {lappend drivers [list port [$bt getName]]}}
 foreach it [$net getITerms] {
  if {![$it isOutputSignal]} continue
  set inst [$it getInst];set m [$inst getMaster];set name [$m getName]
  if {[string match BUF* $name] || [string match *INV* $name]} {
   set ins {};foreach pin [$inst getITerms] {if {[$pin isInputSignal]} {lappend ins $pin}}
   if {[llength $ins]!=1} {error "RESET_COPY_AUDIT unexpectedbufferABI$name"}
   set sig [signature [[lindex $ins 0] getNet] $seen]
   if {[string match *INV* $name]} {
    if {[lindex $sig 0] eq "not"} {set sig [lindex $sig 1]} else {set sig [list not $sig]}
   }
   lappend drivers $sig
  } else {lappend drivers [list cell [root_name [$inst getName]] [[$it getMTerm] getName]]}
 }
 if {[llength $drivers]!=1} {error "RESET_COPY_AUDIT expectedonesignaldriver[$net getName]:[llength $drivers]"}
 return [lindex $drivers 0]
}
proc ot_lpc_audit::loads {net {seen {}}} {
 if {[dict exists $seen $net]} {error "RESET_COPY_AUDIT outputbufferloop"}
 dict set seen $net 1
 set n 0
 foreach it [$net getITerms] {
  if {![$it isInputSignal]} continue
  set inst [$it getInst];set name [[$inst getMaster] getName]
  if {[string match BUF* $name] || [string match *INV* $name]} {
   foreach op [$inst getITerms] {if {[$op isOutputSignal] && ![null [$op getNet]]} {incr n [loads [$op getNet] $seen]}}
  } else {incr n}
 }
 return $n
}
if {[info exists ::ot_lpc_audit_definitions_only] && $::ot_lpc_audit_definitions_only} {return}
if {![info exists ::env(RESULTS_DIR)]} {error "RESET_COPY_AUDIT missingRESULTS_DIR"}
set manifest [file join $::env(RESULTS_DIR) ot_reset_copy_manifest.tcl]
if {![file exists $manifest]} {error "RESET_COPY_AUDIT missingpersistedmanifest$manifest"}
source $manifest
set checked 0
foreach record $::ot_lpc_audit_records {
 lassign $record name master expected
 set inst [$ot_lpc_audit::block findInst $name]
 if {[ot_lpc_audit::null $inst]} {error "RESET_COPY_AUDIT removedstatecopy$name"}
 if {[[$inst getMaster] getName] ne $master} {error "RESET_COPY_AUDIT changedstatemaster$name"}
 dict for {pin sig} $expected {
  set it [$inst findITerm $pin]
  if {[ot_lpc_audit::null $it] || [ot_lpc_audit::signature [$it getNet]] ne $sig} {error "RESET_COPY_AUDIT changedequation$name/$pin"}
 }
 incr checked
}
set max 0;set stages 0
foreach inst [$ot_lpc_audit::block getInsts] {
 if {![[$inst getMaster] isSequential]} continue
 set name [$inst getName]
 if {![regexp $::ot_lpc_audit_match $name] && ![dict exists $::ot_lpc_audit_alias $name]} continue
 incr stages
 foreach op [$inst getITerms] {
  if {![$op isOutputSignal] || [ot_lpc_audit::null [$op getNet]]} continue
  set n [ot_lpc_audit::loads [$op getNet]]
  if {$n>$max} {set max $n}
  if {$n>32} {error "RESET_COPY_AUDIT fanout$n exceeds32 on$name"}
 }
}
puts "RESET_COPY_AUDIT PASS retained_state_copies=$checked stages=$stages maximum_buffer_tree_terminal_load=$max clock_and_data_equations=UNCHANGED"
