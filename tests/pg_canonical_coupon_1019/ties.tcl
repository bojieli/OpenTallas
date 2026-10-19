set p /OpenROAD-flow-scripts/flow/platforms/asap7
foreach n {AO OA INVBUF SEQ SIMPLE} {
 set suffix [expr {$n eq "SEQ" ? "220123.lib" : $n eq "INVBUF" ? "220122.lib.gz" : "211120.lib.gz"}]
 read_liberty $p/lib/NLDM/asap7sc7p5t_${n}_RVT_TT_nldm_$suffix
}
read_db /src/map_v2/results/asap7/pg_canonical_coupon_1019/base/1_synth.odb
set c TIEHIx1_ASAP7_75t_R
set lib [get_name [get_property [lindex [get_lib_cell $c] 0] library]]
# Same actual command/pin resolution as canonical floorplan.tcl. This
# unplaced topology coupon makes no placement or timing-quality claim.
repair_tie_fanout -separation 0 $lib/$c/H
write_db /src/evidence_native_v3/ties.odb
write_verilog /src/evidence_native_v3/ties.v
exit
