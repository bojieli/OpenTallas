# Read-only analytical native budget, no physical evidence.
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
read_liberty {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
read_liberty {/src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_ff.lib}
read_liberty {/src/physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_ff.lib}
read_liberty {/src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib}
read_liberty {/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ff.lib}
set_units -time ps
read_db /native/results/asap7/opentallas_dsdv_eng_rr_asap7_native/base/1_synth.odb
read_sdc /native/constraint.sdc
puts "INTRINSIC_BUDGET_MODEL_ONLY_ZERO_WIRE_FF"
report_checks -path_delay min -group_path_count 20 -format full_clock_expanded -fields {slew cap fanout} -digits 6
report_worst_slack -min
