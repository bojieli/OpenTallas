read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_LVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_SLVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_SLVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_SLVT_FF_nldm_220122.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_SLVT_FF_nldm_220122.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_LVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_SLVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_SLVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_FF_nldm_220123.lib]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_LVT_FF_nldm_220123.lib}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_SLVT_FF_nldm_220123.lib]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_SLVT_FF_nldm_220123.lib}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_LVT_FF_nldm_211120.lib.gz}
if {[file exists /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_SLVT_FF_nldm_211120.lib.gz]} {read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_SLVT_FF_nldm_211120.lib.gz}
read_db /in/6_final.odb
read_sdc /in/6_final.sdc
read_spef /in/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_FF_WS setup_ns=[sta::worst_slack_cmd max] hold_ns=[sta::worst_slack_cmd min]"
write_timing_model -library_name hgi_mtp_native_ff /w/hgi_mtp_native_ff.lib
puts OT_EXPORT_DONE
exit
