# MU-KV-CTX bench tb_mu_kvctx: every file the build reads (the ctlm list rtl/test/qwen_dv/tt_ctlm_dv_sources.f + the KV / compute MU context files)
rtl/qwen_dv/qfd_tt_ctlm_dv.sv
rtl/qwen_dv/qfd_dv_hr_pack.sv
rtl/qwen_dv/qfd_dv_cmd_cal.sv
rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv
rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_split_static.sv
rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_hr.sv
rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_head_static_rk.sv
rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_static.sv
rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv
rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_pw.sv
rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_dense_pw.sv
rtl/qwen_sys/static_schedule_20261014/ot_qfd_native_cmd_route.sv
rtl/qwen_sys/static_schedule_20261014/ot_qwen_tp8_rom_relocate.sv
rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_dense_pw_loader.sv
rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_static_schedule.sv
rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv
rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv
rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv
rtl/physical/ot_qfd_tt_ctlm_split.sv
rtl/hdc/ot_hdc_prefix.sv
rtl/hdc/ot_hdc_delay.sv
rtl/lib/ot_reset_sync.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
rtl/hdc/ot_hdc_dyn_ttiles.sv
rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv
rtl/hdc/ot_hdc_cg.sv
rtl/hdc/ot_hdc_sfu.sv
rtl/hdc/ot_qwen_me_spine_h_w12.sv
rtl/hdc/ot_qwen_w12_arith.sv
rtl/hdc/ot_qwen_w12_matvec.sv
rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctl_static.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
rtl/qwen_split/mu/qfd_sys_face_mu_dhuser.sv
physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v
rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
rtl/qwen_sys/context_transport_20261014/qkd_host_record_port.sv
rtl/qwen_sys/mu_qwen_20261018/qkd_host_record_port_mu.sv
rtl/qwen_split/mu/qfd_mu_ctx_rx.sv
# CAL mode (MU-DQ-SYSFACE 10-19): both link ends' real D2D sequencers (MU image, the qfd_sys_face MU kit's source) + calendar playback
rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv
rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv
rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv
rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv
rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq_dies_mu.sv
rtl/test/mu_qwen_1018/tb_mu_kvctx.sv
# included: rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh (-I); read by the bench script: d2d_cal_image_mu.svh, d2d_cal_image.svh
# python inputs (not compiled; mu_kvctx_bench.py imports rtl/test/mu_qwen_seq/mu_opseg_bench.py unchanged):
# rtl/test/mu_qwen_1018/mu_kvctx_bench.py
# rtl/test/mu_qwen_seq/mu_opseg_bench.py
# rtl/test/qwen_dv/tt_ctlm_dv_sources.f
# tools/qwen_static_schedule/ (mu_opcal.py, calendar.py and their package imports)
# tools/hdc_isa.py
# tools/hdc_golden.py
# tools/qwen_coll_tp8_bench.py
# tools/qwen_coll_tp8_static_bench.py
# results/arch/qwen_kv_static_programme_1017/die/report.json
