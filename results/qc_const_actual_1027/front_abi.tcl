yosys read_verilog -sv -lib /work/bb/ot_sram_1r1w_256x256_m2_r2c2.v /work/bb/ot_sram_1r1w_1024x256_m2_r2c2.v /work/bb/ot_sram_1r1w_32x64_m1.v /work/bb/ot_sram_1r1w2c_128x64_m1.v
yosys read_verilog -sv -defer -DSYNTHESIS -I/work/inputs/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1 -I/work/inputs/physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2 -I/work/inputs/physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2 -I/work/inputs/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1 -I/work/inputs/rtl/dsrom_sys/s81_window_la/recovered_ctl_m2 -I/work/inputs/rtl/hbm_accel/generic/collective/inverse -I/work/inputs/rtl/hdc -I/work/inputs/rtl/lib -I/work/inputs/rtl/physical -I/work/inputs/rtl/proto -I/work/inputs/rtl/qwen_dv -I/work/inputs/rtl/qwen_dv/headprep13/physical_abi -I/work/inputs/rtl/qwen_dv/mu -I/work/inputs/rtl/qwen_dv/s5 -I/work/inputs/rtl/qwen_sys/dvm_20261014 /work/inputs/rtl/physical/qfd_qc_su_lane_w_l0.sv /work/inputs/rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv /work/inputs/rtl/hdc/ot_hdc_delay.sv /work/inputs/rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv /work/inputs/rtl/lib/ot_rst_pipe.sv /work/inputs/rtl/hbm_accel/generic/collective/inverse/ot_hgi_inverse_sram_mask_sim.sv /work/inputs/rtl/qwen_dv/qfd_dv_stream.sv /work/inputs/rtl/qwen_dv/qfd_dv_slice_tload.sv /work/inputs/rtl/qwen_dv/qfd_dv_table_rom_loader.sv /work/inputs/rtl/qwen_dv/headprep13/physical_abi/ot_rom_4096x266_m8_bb.sv /work/inputs/rtl/qwen_dv/qfd_dv_scalar2.sv /work/inputs/rtl/hdc/ot_hdc_sfu.sv /work/inputs/rtl/hdc/ot_hdc_fpu.sv /work/inputs/rtl/hdc/ot_hdc_fp32_mul_pipe.sv /work/inputs/rtl/proto/ot_fp32_add_rne_pipe.sv /work/inputs/rtl/hdc/ot_hdc_sfu_q.sv /work/inputs/rtl/hdc/ot_hdc_fastfp.sv /work/inputs/rtl/hdc/ot_hdc_fp32_mul_lat.sv /work/inputs/rtl/hdc/ot_hdc_fp32_add_lat.sv /work/inputs/rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv /work/inputs/rtl/hdc/ot_hdc_vreduce.sv /work/inputs/rtl/qwen_dv/s5/qfd_dv_s5_vm.sv /work/inputs/rtl/qwen_dv/mu/qfd_dv_amax_mu.sv /work/inputs/rtl/qwen_dv/qfd_dv_head_safe1.sv /work/inputs/rtl/hdc/ot_hdc_vstream_sfu_t.sv
yosys hierarchy -check -top qfd_qc_su_lane_w_l0
yosys proc
yosys flatten
yosys opt_expr
set ::env(DESIGN_NAME) qfd_qc_su_lane_w_l0
set ::env(OT_KEEP_PIN_REGS) 1
set ::env(RESULTS_DIR) /work/front
source /work/tools/ot_keep_regs.tcl
yosys write_json /work/front/pre.json
yosys write_rtlil /work/front/pre.il
yosys stat
