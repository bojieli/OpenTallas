#!/bin/bash
set -euo pipefail
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
H=rtl/hdc;D=$H/v41x
SRC=(tools/s81_dv/svc_rs/merge_sram/tb_merge.sv tools/s81_dv/svc_rs/merge_sram/merge_ref.sv "$D/ot_hdc_v41x_attn_s.sv" "$D/ot_hdc_v41x_merge_ring_sram.sv" "$D/ot_hdc_v41x_attn.sv" "$D/ot_hdc_v41x_attn_tile_s.sv" "$D/ot_hdc_v41x_attn_tile.sv" "$D/ot_hdc_v41x_kreg.sv" "$H/ot_hdc_delay.sv" "$H/ot_hdc_fastfp.sv" "$H/ot_hdc_fastfp_lat_f12.sv" "$H/ot_hdc_fp32_f12.sv" "$H/ot_hdc_fp32_add_lat.sv" "$H/ot_hdc_prefix.sv" "$D/ot_dsrom_su_add6.sv" physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v)
sha256sum "${SRC[@]}" > ../out/merge_sources.sha256
"$V" --binary --timing -j 4 -CFLAGS -O1 --top-module tb_merge -DOT_SVC_MERGE_SRAM -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --Mdir ../out/obj_merge "${SRC[@]}" > ../out/merge_build.log 2>&1
../out/obj_merge/Vtb_merge > ../out/merge_run.log 2>&1
cat ../out/merge_run.log
