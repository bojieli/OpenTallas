read_db /probe/work/orfs/results/asap7/opentallas_ot_v41_static_provider_context_asap7_epicurus_static_context_r1/base/2_floorplan.odb
set b [ord::get_db_block]
puts "DBU [$b getDbUnitsPerMicron]"
foreach r [$b getRegions] {puts "REGION [$r getName] [$r getRegionType]";foreach z [$r getBoundaries] {puts "BOX [$z xMin] [$z yMin] [$z xMax] [$z yMax]"}}
foreach g [$b getGroups] {puts "GROUP [$g getName] TYPE [$g getType] NINST [llength [$g getInsts]]"}
exit
