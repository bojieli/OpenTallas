sc_check after_dpl firm
# Restore intended statuses only after strict endpoint and source checks.
dict for {name st} $::sc_expected_cells {
 if {[sc_endpoint $name $st]} {set i [$::scb findInst $name];$i setPlacementStatus [lindex $st 3]}
}
sc_check final_place original
source /work/pg_connect.tcl
ot_pg_require_bound sc_final_place
# Preserve the actual successful DPL state before the read-only observer.
write_db /work/sc_final_place_retained.odb
set ::env(OT_GEOM_OUT) /work/sc_final_place_geom.tsv
uplevel #0 [list source /work/geom_dump.tcl]
