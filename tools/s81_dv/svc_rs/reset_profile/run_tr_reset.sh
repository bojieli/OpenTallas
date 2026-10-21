#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p ../out_tr_reset_asr
D=rtl/hdc/v41x
SRC=(rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_glue.sv tools/s81_dv/svc_rs/reset_profile/tb_tr_reset.sv rtl/dsrom_sys/s81_dv/svc_rs/ot_s81svc_reset9_n32.sv tools/s81_dv/svc_rs/merge_sram/tr_ref.sv "$D/ot_hdc_v41x_attn_s.sv" "$D/ot_hdc_v41x_attn_tr_sram.sv" "$D/ot_hdc_v41x_kreg.sv" physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v)
sha256sum "${SRC[@]}" > ../out_tr_reset_asr/tr_sources.sha256
"$V" --binary --timing -j 4 -CFLAGS -O1 -Irtl/dsrom_sys/s81_dv/svc_rs --top-module tb_tr_reset -DOT_SVC_TR_SRAM -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --Mdir ../out_tr_reset_asr/obj_tr "${SRC[@]}" > ../out_tr_reset_asr/tr_build.log 2>&1
../out_tr_reset_asr/obj_tr/Vtb_tr_reset > ../out_tr_reset_asr/tr_run.log 2>&1
cat ../out_tr_reset_asr/tr_run.log
