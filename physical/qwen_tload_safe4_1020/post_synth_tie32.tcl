# Source-bound constant-copy repair. Exact masters/pins/functions are bound to this immutable Liberty.
set lib /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
set expected 073ac4b6b08f272b6953b0ad54d1d9743767a7d15a0e2964ed86cf44c3dbe00e
if {[lindex [exec sha256sum $lib] 0] ne $expected} {error "TLOAD_CONST32 Liberty SHA mismatch"}
set const [dict create TIEHIx1_ASAP7_75t_R {H 1} TIELOx1_ASAP7_75t_R {L 0}]
set b [ord::get_db_block]
proc tload_const_source {net allowed} {
 set ds {};foreach t [$net getITerms] {if {[$t getIoType] eq "OUTPUT"} {lappend ds $t}}
 if {[llength $ds]!=1} {return {}}
 set d [lindex $ds 0];set master [[$d getInst] getMaster];set m [$master getName]
 if {![dict exists $allowed $m]} {return {}}
 if {[[$d getMTerm] getName] ne [lindex [dict get $allowed $m] 0]} {error "TLOAD_CONST32 pin role mismatch"}
 if {[llength [$net getBTerms]]!=0} {error "TLOAD_CONST32 tied top port"}
 return [list $d $master [lindex [dict get $allowed $m] 1]]
}
set before [dict create]
foreach i [$b getInsts] {foreach t [$i getITerms] {set n [$t getNet];dict set before "[$i getName]/[[$t getMTerm] getName]" [expr {$n eq "NULL" ? "" : [$n getName]}]}}
set copies 0;set moved 0
foreach n [$b getNets] {
 set src [tload_const_source $n $const];if {$src eq {}} {continue}
 set ss {};foreach t [$n getITerms] {if {[$t getIoType] eq "INPUT"} {lappend ss $t}}
 for {set off 32} {$off<[llength $ss]} {incr off 32} {
  set name "tload_const_copy32_$copies";if {[$b findInst $name] ne "NULL"} {error "TLOAD_CONST32 duplicate copy"}
  set cp [odb::dbInst_create $b [lindex $src 1] $name];set nn [odb::dbNet_create $b "${name}_net"]
  [$cp findITerm [[[lindex $src 0] getMTerm] getName]] connect $nn
  foreach t [lrange $ss $off [expr {$off+31}]] {$t disconnect;$t connect $nn;incr moved}
  incr copies
 }
}
# Every moved original input remains on the same exact constant master/function. No signal or reset is filtered.
foreach i [$b getInsts] {foreach t [$i getITerms] {
 set key "[$i getName]/[[$t getMTerm] getName]";if {![dict exists $before $key]} {continue}
 set n [$t getNet];set now [expr {$n eq "NULL" ? "" : [$n getName]}];set old [dict get $before $key]
 if {$old eq $now} {continue}
 if {[$t getIoType] ne "INPUT" || [$t getSigType] in {CLOCK POWER GROUND}} {error "TLOAD_CONST32 unexpected changed pin $key"}
 set a [tload_const_source [$b findNet $old] $const];set z [tload_const_source $n $const]
 if {$a eq {} || $z eq {} || [[lindex $a 1] getName] ne [[lindex $z 1] getName] || [lindex $a 2] ne [lindex $z 2]} {error "TLOAD_CONST32 signal identity failed $key"}
}}
puts "TLOAD_CONST32_COPY PASS copies=$copies sinks=$moved exact_Lib_SHA=$expected"
