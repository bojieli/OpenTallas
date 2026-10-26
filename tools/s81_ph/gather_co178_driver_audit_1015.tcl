# Run against the actual candidate CTS or final ODB, never a donor netlist.
# Geometry/driver identity proof only; full TT/FF/DRC remain separate gates.
read_db $::env(S81_AUDIT_ODB)
set b [ord::get_db_block]
set port [$b findBTerm {co[178]}]
if {$port eq "NULL"} {error "S81_CO178_AUDIT missing actual output"}
set net [$port getNet]
set seen {};set chain {};set found 0
for {set hop 0} {$hop<32} {incr hop} {
 if {$net eq "NULL" || [$net getId] in $seen} {error "S81_CO178_AUDIT null/cyclic data cone"}
 lappend seen [$net getId]
 set drivers {}
 foreach pin [$net getITerms] {
  if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $pin}
 }
 if {[llength $drivers]!=1} {error "S81_CO178_AUDIT data cone must have one actual driver"}
 set driver [lindex $drivers 0];set inst [$driver getInst];set master [[$inst getMaster] getName]
 lappend chain [list [$inst getName] $master [[$driver getMTerm] getName]]
 if {[$inst getName] eq "ot_prs_00083_ff"} {
  if {![string match DFF* $master]} {error "S81_CO178_AUDIT named driver is not actual FF"}
  set cp [$inst findITerm CLK]
  if {$cp eq "NULL" || [$cp getNet] eq "NULL" || [[$cp getNet] getSigType] ne "CLOCK"} {error "S81_CO178_AUDIT no actual clock"}
  puts "S81_CO178_AUDIT actual dedicated driver [$inst getName] clock [[ $cp getNet] getName] chain=$chain"
  set found 1;break
 }
 if {![regexp {^(BUF|HB|INV)} $master]} {error "S81_CO178_AUDIT unexpected combinational master $master"}
 set inputs {}
 foreach pin [$inst getITerms] {
  if {[[$pin getMTerm] getIoType] eq "INPUT" && [[$pin getMTerm] getSigType] ni {POWER GROUND}} {lappend inputs $pin}
 }
 if {[llength $inputs]!=1} {error "S81_CO178_AUDIT non-buffer data cone"}
 set net [[lindex $inputs 0] getNet]
}
if {!$found} {error "S81_CO178_AUDIT expected FF not found on actual co178 cone"}
puts "S81_CO178_AUDIT PASS"
exit
