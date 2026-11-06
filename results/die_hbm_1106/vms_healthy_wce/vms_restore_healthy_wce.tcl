# Restore and hold exactly ONE unchanged healthy DATA route. No clock edits.
read_db $::env(VMS_TARGET_ODB)
source /work/clk_freeze.tcl
set block [ord::get_db_block];set tech [[$block getDb] getTech]
set target [$block findNet net22261]
set rdb [odb::dbDatabase_create]
odb::read_db $rdb $::env(VMS_REFERENCE_ODB)
set rb [[$rdb getChip] getBlock];set ref [$rb findNet net22261]
proc endpoint_state {net} {
 set out {}
 foreach t [$net getITerms] {
  set i [$t getInst]
  lappend out [list [$i getName] [[$t getMTerm] getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]]
 }
 return [lsort $out]
}
if {[$target getSigType] ne "SIGNAL" || [$ref getSigType] ne "SIGNAL"} {error "expected DATA net"}
if {[endpoint_state $target] ne [endpoint_state $ref]} {error "endpoint/master/placement changed"}
if {[llength [$target getITerms]] != 2 || [[$ref getWire] length] != 313} {error "unexpected reference"}
set names {}
foreach t [$target getITerms] {lappend names "[[$t getInst] getName]/[[$t getMTerm] getName]"}
if {[lsort $names] ne {u_fcore.u_core.u_ot_pr_core.bank.u_b/w_ce_in wire22262/Y}} {error "wrong net endpoints"}
set ops {}
foreach a [ot_clk_wire_ops $ref] {
 set cmd [lindex $a 0]
 switch $cmd {
  wireProperty {continue}
  newPath {
   if {[llength $a] != 3} {error "unexpected path rule $a"}
   set x [lindex $a 1]
   if {![string is integer -strict $x]} {lset a 1 [$tech findLayer [$x getName]]}
  }
  newPathExt {}
  newPathShort - newPathVirtualWire {
   if {[llength $a] != 4} {error "unexpected short/vwire rule"}
   set l [lindex $a 2];lset a 2 [$tech findLayer [$l getName]]
  }
  addTechVia {set v [lindex $a 1];lset a 1 [$tech findVia [$v getName]]}
  addITerm {set t [lindex $a 1];lset a 1 [[$block findInst [[$t getInst] getName]] findITerm [[$t getMTerm] getName]]}
  addBTerm {error "unexpected top port on internal data net"}
  addPoint - addRect {}
  default {error "unexpected reference op $cmd"}
 }
 lappend ops $a
}
set nw [odb::dbWire_create $block];set enc [odb::dbWireEncoder];$enc begin $nw
foreach a $ops {$enc {*}$a}
$enc end
odb::dbWire_destroy [$target getWire];$nw attach $target
proc physical_tokens {net} {
 set out {}
 foreach t [ot_clk_wire_tokens $net] {if {[lindex $t 0] != 12} {lappend out $t}}
 return $out
}
if {[physical_tokens $target] ne [physical_tokens $ref] || [ot_clk_wire_types $target] ne {64}} {error "reference geometry/connectivity not preserved"}
# Preserve the healthy driver position/master while its exact wire is fixed.
$target setDoNotTouch 1
set d [$block findInst wire22262]
$d setPlacementStatus LOCKED
$d setDoNotTouch 1
write_db $::env(VMS_OUTPUT_ODB)
puts "VMS_WCE_RESTORE PASS: net22261 exact DRC0 reference metal/vias/endpoints/placements, DATA wire FIXED and healthy driver locked; all clock nets untouched; cycles0"
odb::dbDatabase_destroy $rdb
