read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_db /g/routes/gate/work/orfs/results/asap7/opentallas_dsdv_gunit_l5_asap7_ref_gate/base/4_1_cts.odb
write_abstract_lef -bloat_occupied_layers /out/dsdv_gunit_l5.lef
puts OT_EXPORT_DONE
exit
