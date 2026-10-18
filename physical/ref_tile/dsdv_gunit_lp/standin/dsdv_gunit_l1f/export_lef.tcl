read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /g/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef
read_db /g/routes/gate/work/orfs/results/asap7/opentallas_dsdv_gunit_l1f_asap7_ref_gate/base/4_1_cts.odb
write_abstract_lef -bloat_occupied_layers /out/dsdv_gunit_l1f.lef
puts OT_EXPORT_DONE
exit
