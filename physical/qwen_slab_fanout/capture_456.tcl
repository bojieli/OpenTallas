# Additive item7 recipe, run as selected MACRO_PLACEMENT_TCL. No clock/IO exception.
source /src/physical/qwen_slab_share/macro_place_h455.76.tcl
# Bind actual netlist input endpoints, not an assumed auto-generated FF name.
# Refuse any buffer/mux expansion here: update the source-selected census first.
set cap_block [ord::get_db_block]
set cap_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set cap_seen [dict create]
for {set c 0} {$c < 4} {incr c} {
  set region [odb::dbRegion_create $cap_block "capture_col_$c"]
  $region setRegionType FENCE
  set x0 [expr {40.0 + $c * (775.416 - 40.0) / 4.0}]
  set x1 [expr {40.0 + ($c + 1) * (775.416 - 40.0) / 4.0}]
  odb::dbBox_create $region [expr {round($x0*$cap_dbu)}] [expr {round(427.68*$cap_dbu)}] [expr {round($x1*$cap_dbu)}] [expr {round(453.6*$cap_dbu)}]
  set group [odb::dbGroup_create $cap_block "capture_col_$c"]
  $group setRegion $region
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
