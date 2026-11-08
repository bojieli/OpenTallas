read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /k/macros/ot_sram_1r1w_1024x256_m2_r2c2.lef
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {read_liberty $l}
read_liberty /k/macros/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib
read_db /k/run/results/asap7/hbc_hnx_vms_bank_q0_faces__vecd4ae/base/1_synth.odb
read_sdc /k/run/results/asap7/hbc_hnx_vms_bank_q0_faces__vecd4ae/base/1_synth.sdc
set f [open /out/xroot.tsv w]
set ::env(RESULTS_DIR) /out; source /w/vecd_xlk.tcl; write_verilog /out/xlk_test.v; puts XLK_TEST_OK
