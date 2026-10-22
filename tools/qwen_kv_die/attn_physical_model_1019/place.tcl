foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {read_liberty $lib}
read_db /work/synth/results/asap7/opentallas_qkd_kvs_attn_safe_control_asap7_ref_gate/base/1_synth.odb
initialize_floorplan -die_area {0 0 216 216} -core_area {2.16 86.4 213.84 129.6} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
source /work/pins.tcl
place_pins -hor_layers M4 -ver_layers M5 -min_distance 0.1667
place_pin -pin_name ck -layer M5 -location {216 108} -force_to_die_boundary
write_db /work/2_floorplan.odb
set_thread_count 8
global_placement -density 0.50 -skip_io -overflow 0.1
write_db /work/3_global.odb
detailed_placement
check_placement -verbose
write_db /work/3_placed.odb
write_verilog /work/3_placed.v
