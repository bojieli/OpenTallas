read_db /case/routes/gate/work/orfs/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base/1_synth.odb
set b [ord::get_db_block];set u [[ord::get_db_tech] getDbUnitsPerMicron]
if {[llength [$b getRows]] || [llength [$b getGroups]]} {error "MODEL fresh synth expected no placement rows/groups"}
set site ""
foreach i [$b getInsts] {if {![[$i getMaster] isBlock] && [[$i getMaster] getSite] ne "NULL"} {set site [[[$i getMaster] getSite] getName];break}}
initialize_floorplan -die_area {0 0 561.6 388.8} -core_area {2.16 2.16 559.44 386.64} -site $site
source /src/physical/ref_tile/dsdv_mu_hwin_c21n/place.tcl
cut_rows -halo_width_x 8.64 -halo_width_y 8.64
set band 0;set area 0.0
foreach row [$b getRows] {
 set r [$row getBBox]
 if {[$r yMin]>=round(159.84*$u) && [$r yMax]<=round(206.28*$u)} {
  if {[$r xMin]!=round(2.16*$u) || [$r xMax]!=round(559.44*$u)} {error "MODEL fullwidth band rowhole"}
  incr band;set area [expr {$area+double([$r xMax]-[$r xMin])*([$r yMax]-[$r yMin])/$u/$u}]
 }
}
if {$band!=172 || abs($area-25880.0832)>0.0001} {error "MODEL changed band footprint band=$band area=$area"}
puts "MODEL_FULL_CORE_ROWS_BAND_FOOTPRINT_PASS total_rows=[llength [$b getRows]] band_rows=$band band_area=$area planning_only_density=[expr {11063.90178/$area}] actual40..60_not_waived=1"
write_db /audit/hwin_fresh_full_rows_model.odb
