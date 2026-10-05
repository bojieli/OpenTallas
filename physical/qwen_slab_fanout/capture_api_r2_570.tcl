# Additive item7 recipe, run as selected MACRO_PLACEMENT_TCL. No clock/IO exception.
source /src/physical/qwen_slab_share/macro_place_h570.24.tcl
# Bind actual netlist input endpoints, not an assumed auto-generated FF name.
# Refuse any buffer/mux expansion here: update the source-selected census first.
set cap_block [ord::get_db_block]
set cap_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cap_seen [dict create]
for {set c 0} {$c < 4} {incr c} {
  set region [odb::dbRegion_create $cap_block "capture_col_$c"]
  # Pinned OpenDB EXCLUSIVE writes DEF TYPE FENCE; hard inside/exclusion semantics.
  $region setRegionType EXCLUSIVE
  set x0 [expr {40.0 + $c * (775.416 - 40.0) / 4.0}]
  set x1 [expr {40.0 + ($c + 1) * (775.416 - 40.0) / 4.0}]
  odb::dbBox_create $region [expr {round($x0*$cap_dbu)}] [expr {round(540*$cap_dbu)}] [expr {round($x1*$cap_dbu)}] [expr {round(568.08*$cap_dbu)}]
  set group [odb::dbGroup_create $cap_block "capture_col_$c"]
  $region addGroup $group
  for {set b [expr {128*$c}]} {$b < 128*($c+1)} {incr b} {
    set port [$cap_block findBTerm [format {res_in[%d]} $b]]
    if {$port == "NULL"} { error "capture census missing res_in bit $b" }
    set endpoints {}
    foreach pin [[$port getNet] getITerms] {
      if {[$pin getIoType] == "INPUT"} { lappend endpoints $pin }
    }
    if {[llength $endpoints] != 1} { error "capture bit $b does not have exactly one direct endpoint" }
    set pin [lindex $endpoints 0]
    if {[[$pin getMTerm] getName] != "D"} { error "capture bit $b endpoint is not a D pin" }
    set inst [$pin getInst]
    if {![string match *DFF* [[$inst getMaster] getName]]} { error "capture bit $b endpoint is not a DFF" }
    if {[dict exists $cap_seen [$inst getName]]} { error "capture FF counted twice" }
    dict set cap_seen [$inst getName] 1
    $group addInst $inst
  }
}
if {[dict size $cap_seen] != 512} { error "capture FF census !=512" }
puts "ITEM7_CAPTURE_GROUPS 4 FF_ENDPOINTS 512"

set repair_total 0
for {set c 0} {$c < 4} {incr c} {
  set r [$cap_block findRegion "capture_col_$c"]
  set g [$cap_block findGroup "capture_col_$c"]
  if {[$r getRegionType] != "EXCLUSIVE"} {error "capture region is not hard EXCLUSIVE"}
  if {[llength [$r getGroups]] != 1} {error "capture region does not have one group"}
  if {[[$g getRegion] getName] != [$r getName]} {error "capture group region mismatch"}
  if {[llength [$g getInsts]] != 128} {error "capture group membership !=128"}
  if {[llength [$r getBoundaries]] != 1} {error "capture region rectangle count changed"}
  incr repair_total [llength [$g getInsts]]
  puts "CAPTURE_API_GROUP $c TYPE [$r getRegionType] FF [llength [$g getInsts]]"
}
if {$repair_total !=512 || [dict size $cap_seen] !=512} {error "capture unique membership !=512"}
puts "CAPTURE_API_MEMBERSHIP_PASS 4 EXCLUSIVE_GROUPS 512 UNIQUE_FF"
