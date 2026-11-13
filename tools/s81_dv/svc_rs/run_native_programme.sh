#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?outdir}")
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"
OBJ=${OBJ_DIR:-$O/obj}
files=(rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_s81c_attn_hcore.sv rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv rtl/dsrom_sys/s81_dv/ot_s81_svc_merge_h4.sv rtl/dsrom_sys/s81_svc/ot_s81_svc_band.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_la.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_lr.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v physical/asap7_memory_macros_v2/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v)
"$VL" --binary --timing --top-module tb_svc_native_programme -Mdir "$OBJ" -j 8 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --output-split 20000 --output-split-cfuncs 2000 -fno-inline -MAKEFLAGS OPT_FAST=-O1 -DOT_SVC_MERGE_H4 -DOT_ATTN_HCORE -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2 -DOT_SVC_NATIVE_RT2_CALENDAR -DOT_S81C_TILE_PAIR -DOT_S81C_TILE_REACH -DOT_SVC_BAND -DOT_SVC_SRX=1 -DOT_SVC_ATT_MEM_MACRO -y rtl/hdc/v41x -y rtl/hdc -y rtl/dsrom_sys/s81_svc -y rtl/dsrom_sys/s81_dv "${files[@]}" rtl/dsrom_sys/s81_dv/svc_rs/test/tb_svc_native_programme.sv >"$O/build.log" 2>&1
"$OBJ/Vtb_svc_native_programme" >"$O/run.log" 2>&1
cat "$O/run.log"
grep -q '^NATIVE_PROGRAMME PASS' "$O/run.log"
python3 tools/s81_dv/svc_rs/check_native_programme_oracle.py "$O/run.log"
