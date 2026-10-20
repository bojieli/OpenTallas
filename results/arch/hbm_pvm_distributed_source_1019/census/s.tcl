yosys read_verilog -sv -DSYNTHESIS rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/gpu/ot_gpu_fadd.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_bb.v rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_s3.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_distributed_core.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_distributed.sv rtl/hbm_accel/sm/attn/test/pvm_reference_pin_wrapper.sv
yosys hierarchy -check -top ot_hbm_sm_pv_merge_distributed
source physical/common_flow/ot_keep_regs.tcl
yosys synth -top ot_hbm_sm_pv_merge_distributed -flatten
yosys dfflibmap -liberty /srv/opentallas-scratch/claude/l2h-pvmd/census/libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
yosys abc -liberty /srv/opentallas-scratch/claude/l2h-pvmd/census/libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty /srv/opentallas-scratch/claude/l2h-pvmd/census/libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty /srv/opentallas-scratch/claude/l2h-pvmd/census/libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty /srv/opentallas-scratch/claude/l2h-pvmd/census/libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib
yosys opt_clean -purge
yosys tee -o ../census_out/dist_hook/stat.txt stat -liberty /srv/opentallas-scratch/claude/l2h-pvmd/census/libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
yosys write_verilog -noattr ../census_out/dist_hook/net.v
