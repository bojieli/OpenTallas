set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT*TT*.lib*] {read_liberty $l}
foreach l [glob /src/physical/asap7_memory_macros/*/*_tt.lib] {read_liberty $l}
read_db /case/routes/gate/work/orfs/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base/3_5_place_dp-failed.odb
set b [ord::get_db_block]
set mode $::env(AUDIT_MODE)
if {$mode eq "full"} {
 set site [[lindex [$b getRows] 0] getSite]
 initialize_floorplan -die_area {0 0 561.6 388.8} -core_area {2.16 2.16 559.44 386.64} -site [$site getName]
 cut_rows -halo_width_x 8.64 -halo_width_y 8.64
}
puts "ROW_INDEX_DIAGNOSTIC mode=$mode rows=[llength [$b getRows]] groups=[llength [$b getGroups]]"
set rc [catch {optimize_mirroring} detail]
puts "ROW_INDEX_DIAGNOSTIC optimize_mirroring_rc=$rc detail=$detail"
set rc [catch {check_placement} detail]
puts "ROW_INDEX_DIAGNOSTIC check_placement_rc=$rc detail=$detail"
if {$mode eq "full"} {write_db /audit/hwin_full_rows_model.odb}
