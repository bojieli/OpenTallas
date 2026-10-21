#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p ../out_tr_r3
D=rtl/hdc/v41x
SRC=(tools/s81_dv/svc_rs/merge_sram/tb_tr.sv tools/s81_dv/svc_rs/merge_sram/tr_ref.sv "$D/ot_hdc_v41x_attn_s.sv" "$D/ot_hdc_v41x_attn_tr_sram.sv" "$D/ot_hdc_v41x_kreg.sv" physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v)
sha256sum "${SRC[@]}" > ../out_tr_r3/tr_sources.sha256
"$V" --binary --timing -j 4 -CFLAGS -O1 --top-module tb_tr -DOT_SVC_TR_SRAM -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --Mdir ../out_tr_r3/obj_tr "${SRC[@]}" > ../out_tr_r3/tr_build.log 2>&1
../out_tr_r3/obj_tr/Vtb_tr > ../out_tr_r3/tr_run.log 2>&1
cat ../out_tr_r3/tr_run.log
