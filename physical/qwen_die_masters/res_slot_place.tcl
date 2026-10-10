# One SRAM, with full 32um pin/capture corridors on every edge.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set count 0
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} {
  place_macro -macro_name [$i getName] -location {43.2 123.12} -orientation R0
  incr count
 }
}
if {$count != 1} {error "res_slot_place requires exactly one SRAM: $count"}
