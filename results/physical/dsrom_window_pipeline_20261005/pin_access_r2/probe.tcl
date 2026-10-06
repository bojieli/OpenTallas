set_thread_count 16
define_corners WC BC
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty -corner WC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty -corner BC /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz
read_db /old_work/results/asap7/opentallas_ot_dsrom_window_pipeline_context_asap7_window_full_pipeline_r1/base/3_1_place_gp_skip_io.odb
read_sdc /old_work/results/asap7/opentallas_ot_dsrom_window_pipeline_context_asap7_window_full_pipeline_r1/base/2_floorplan.sdc
place_pins -hor_layers {M4 M6 M8} -ver_layers {M5 M7 M9}
set block [ord::get_db_block]
set placed 0
foreach bt [$block getBTerms] {
  if {[llength [$bt getBPins]] > 0} {incr placed}
}
puts "WINDOW_PIN_PROBE_TERMINALS [llength [$block getBTerms]] WITH_PINS $placed"
write_db /out/three_pair_pins.odb
puts WINDOW_PIN_PROBE_COMPLETE
exit
