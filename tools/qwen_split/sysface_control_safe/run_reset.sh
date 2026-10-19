#!/bin/bash
set -eu
python3 tools/qwen_split/sysface_control_safe/build_miter.py --graph cold/original.json --manifest cold/manifest.json --receipt cold/generated/receipt.json --source rtl/qwen_split/qfd_sys_face.sv --out cold/miter ${PHYSICAL_BOUNDARY:+--physical-boundary "$PHYSICAL_BOUNDARY"}
python3 rtl/test/qwen_split/build_sysface_cold_fixture.py . cold/sim_two_epochs/img 0
python3 tools/qwen_split/sysface_control_safe/build_reset_bench.py --graph cold/original.json --receipt cold/generated/receipt.json --out cold/reset_tb.sv
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Irtl/qwen_sys/d2d_static_20261015 --top-module tb_sysface_safe_reset --Mdir cold/reset_obj cold/miter/reference.sv cold/miter/miter.sv cold/generated/parent.sv cold/miter/buffer_model.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v rtl/qwen_split/qfd_sys_face_accepted_mu_ctx.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_ovl_seq.sv rtl/qwen_sys/d2d_static_20261015/qfd_d2d_cal_seq_ovl.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq_dies_mu.sv rtl/qwen_split/qfd_sys_face_record_port.sv rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v cold/reset_tb.sv > cold/reset_build.log 2>&1
cold/reset_obj/Vtb_sysface_safe_reset > cold/reset_run.log 2>&1
cat cold/reset_run.log
