# Same exact mapped membership must remain movable through DPL. Old cland
# release hooks re-FIRM their whole family; this explicit opt-in runs last.
uplevel #0 {
 set lnr_b [ord::get_db_block]
 set lnr_f [open /work/native_tiles_manifest.tsv r];set lnr_cells {};set lnr_seen {}
 foreach lnr_line [split [read $lnr_f] \n] {
  if {$lnr_line eq ""} continue
  lassign [split $lnr_line \t] lnr_n lnr_master lnr_bus lnr_tile
  set lnr_i [$lnr_b findInst $lnr_n]
  if {$lnr_i eq "NULL" || ![[$lnr_i getMaster] isCore] || [dict exists $lnr_seen $lnr_n] || [string first "u_cland_$lnr_bus/" [string map {\\ {}} $lnr_n]]<0} {error "NATIVE_TILES release stale/duplicate member $lnr_n"}
  if {[$lnr_i getGroup] ni {NULL {}}} {error "NATIVE_TILES guide not released before DPL: $lnr_n"}
  dict set lnr_seen $lnr_n 1;lappend lnr_cells $lnr_i
 }
 close $lnr_f
 if {![llength $lnr_cells]} {error "NATIVE_TILES empty release"}
 set lnr_f [open /work/native_tiles_held.tsv r]
 foreach lnr_line [split [read $lnr_f] \n] {
  if {$lnr_line eq ""} continue
  set lnr_n [lindex [split $lnr_line \t] 0]
  if {[dict exists $lnr_seen $lnr_n]} {error "NATIVE_TILES protected member in release $lnr_n"}
 }
 close $lnr_f
 foreach lnr_i $lnr_cells {$lnr_i setPlacementStatus PLACED}
 puts "NATIVE_TILES DPL released [llength $lnr_cells] exact native data cells after family refirm; held controls untouched"
}
