# Source-bound SAFE32 synthesis hook: clone only constant-high unused SETN tie cells.
# No placement, delay exception, buffer traversal filter or functional logic rewrite.
set b [ord::get_db_block]
set copies 0
foreach net [$b getNets] {
 set ds {}; set ss {}
 foreach t [$net getITerms] {
  if {[$t getIoType] eq "OUTPUT"} {lappend ds $t}
  if {[$t getIoType] eq "INPUT"} {lappend ss $t}
 }
 if {[llength $ds]!=1 || [llength $ss]<=32} {continue}
 set d [lindex $ds 0]; set master [[$d getInst] getMaster]
 if {![string match "TIEHI*" [$master getName]]} {continue}
 foreach t $ss {
  if {[[$t getMTerm] getName] ne "SETN"} {error "SAFE32 unexpected tied functional/other pin [$net getName]"}
 }
 for {set off 32} {$off<[llength $ss]} {incr off 32} {
  set cp [odb::dbInst_create $b $master "safe32_tie_$copies"]
  set nn [odb::dbNet_create $b "safe32_tie_net_$copies"]
  [$cp findITerm [[$d getMTerm] getName]] connect $nn
  foreach t [lrange $ss $off [expr {$off+31}]] {$t disconnect; $t connect $nn}
  incr copies
 }
}
set max_loads 0
foreach n [$b getNets] {
 if {[$n getSigType] in {POWER GROUND CLOCK} || [$n getName] eq "ck"} {continue}
 set count 0
 foreach t [$n getITerms] {if {[$t getIoType] eq "INPUT"} {incr count}}
 foreach t [$n getBTerms] {if {[$t getIoType] eq "OUTPUT"} {incr count}}
 if {$count>$max_loads} {set max_loads $count}
 if {$count>32} {error "SAFE32 mapped fanout violation [$n getName]: $count loads"}
}
puts "SAFE32_SYNTH PASS max_loads=$max_loads tie_copies=$copies"
