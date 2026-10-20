set variant $::env(OT_LEP_VARIANT)
if {$variant ni {host nh mu_a mu_h}} {error {variant host|nh|mu_a|mu_h required}}
set top ot_s81sl_lep
set kit s81sl_lep_std32
if {$variant eq "nh"} {set top ot_s81sl_lep_nh;set kit s81sl_lepnh_std32}
if {$variant in {mu_a mu_h}} {set top ot_s81sl_lep_$variant}
set ::env(RESULTS_DIR) /run/physical_preflight/$variant
file mkdir $::env(RESULTS_DIR)
if {[info exists ::env(OT_LEP_INPUT_ODB)]} {
 read_db $::env(OT_LEP_INPUT_ODB)
} else {
 read_db /work/native_orfs_${variant}_land5/results/asap7/$top/base/1_synth.odb
}
initialize_floorplan -die_area {0 0 475.2 561.6} -core_area {2.16 2.16 473.04 559.44} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
source /src/results/rtl/s81_standard_lep_physical_preflight_1020/pins_${variant}.tcl
source /src/physical/dscoll_cx/s81_lep_native_band.tcl
ot_lep_trim_rows
ot_lep_initial_owner
source /src/physical/ref_tile/$kit/place.tcl
# A PG geometry preflight only: std cells are deliberately not placed here.
source /src/physical/ref_tile/$kit/pdn.tcl
pdngen -failed_via_report /run/physical_preflight/$variant/failed_vias.rpt
source /src/physical/common_flow/native_pg_binding.tcl
set fh [open /run/physical_preflight/$variant/pg_binding.json w]
set pg [ot_pg_write_snapshot [ord::get_db_block] $fh]
if {[dict get $pg failure_count] != 0} {error {LEP_PG_BINDING_FAILED}}
set ::env(OT_LAYOUT_OUT) /run/physical_preflight/$variant/layout.json
set ::env(OT_LAYOUT_TOP) $top
source /src/tools/ref_tile/layout_dump.tcl
write_db /run/physical_preflight/$variant/floorplan.odb
puts "LEP_FLOORPLAN_MODEL_PASS variant=$variant no_GPL_CTS_route"
