read_db /work/input.odb
set ::env(RESULTS_DIR) /work/out
file mkdir $::env(RESULTS_DIR)
set ::env(OT_OFLOP_COLS) 4
set ::env(OT_OFLOP_ALLOW_NONE) 1
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
set f [open /work/expected_anchors.txt r]; set expected [lsort [split [string trim [read $f]] "\n"]]; close $f
set f [open /work/out/ot_out_flop_at_pins.txt r]; set actual [lsort [split [string trim [read $f]] "\n"]]; close $f
if {$actual ne $expected} { error "canonical replay anchor identities differ" }
set b [ord::get_db_block]
set mutant $::env(MUTANT)
set path /work/out/ot_out_flop_at_pins.txt
if {$mutant eq "missing_list"} {file delete $path}
if {$mutant eq "duplicate_anchor"} {set f [open $path a]; puts $f [lindex $actual 0]; close $f}
if {$mutant eq "missing_anchor"} {set f [open $path a]; puts $f no_such_instance; close $f}
if {$mutant eq "unfixed_anchor"} {[$b findInst [lindex $actual 0]] setPlacementStatus PLACED}
if {$mutant eq "unexpected_hold"} {close [open /work/out/ot_inhold_firm.txt w]}
if {$mutant eq "unowned_fixed"} {
 foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock] || [$i getName] in $actual} continue
  set connected 0
  foreach t [$i getITerms] {set n [$t getNet]; if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {set connected 1; break}}
  if {$connected} {$i setPlacementStatus FIRM; break}
 }
}
source /work/band.tcl
if {$mutant eq "duplicate_hook"} {source /work/band.tcl}
if {$mutant ne "none"} {error "MUTANT_SURVIVED $mutant"}
set audit_n 0
set audit_anchor 0
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} continue
 set functional 0
 foreach t [$i getITerms] {set n [$t getNet]; if {$n ne "NULL" && [$n getSigType] ni {POWER GROUND}} {set functional 1;break}}
 if {!$functional} continue
 if {[$i getName] in $actual} {
  if {[$i getPlacementStatus] ni {FIRM LOCKED}} {error "audit moved anchor"}
  if {[$i getGroup] ne "NULL"} {error "audit grouped anchor"}
  incr audit_anchor
 } else {
  if {[$i getGroup] eq "NULL" || [[$i getGroup] getName] ne "${pf_name}_group"} {error "audit unfenced functional cell"}
  incr audit_n
 }
}
if {$audit_anchor != [llength $actual]} {error "audit missing anchor"}
puts "ORDER_HARDBAND_PROOF PASS anchors=$audit_anchor nonboundary_fenced=$audit_n classes=$cnt"
write_db /work/out/hardband.odb
