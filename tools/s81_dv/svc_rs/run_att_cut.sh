#!/usr/bin/env bash
# HARD-S81-SVC-1 (11-13): dsdv_svc_att vs dsdv_svc_att_cut (+ CUTMUT 1, 2) lock-step (tb_svc_att_cut), seeds $SEEDS.
# Run from the repo root:  run_att_cut.sh OUT_DIR
set -euo pipefail
O=$(realpath -m "$1"); SEEDS=${SEEDS:-"1 2"}; NCYC=${NCYC:-200000}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
source tools/s81_dv/svc_rs/rs_files.sh
mkdir -p "$O"
A=rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
SRC=(); for f in "${RS_SRC[@]}"; do [ "$f" = "$D/dsdv_svc_rs.sv" ] || SRC+=("$f"); done
printf "%s\n" "${SRC[@]}" | grep -qx "$A" || SRC+=("$A")
SRC+=(rtl/hdc/v41x/ot_s81c_attn_hcore.sv rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv)
M=physical/asap7_memory_macros_v2
"$VL" --binary --top-module tb_svc_att_cut -Mdir "$O/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --unroll-count 16 --unroll-limit 131072 -CFLAGS -O1 -I"$D" -DOT_SVC_ALLQ -DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2 -DOT_ATTN_HCORE \
  -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DSU_SMU_T -DOT_SVC_ATT_MEM_MACRO -GNCYC=$NCYC \
  "${RS_DEF[@]}" rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_cut.sv \
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_la.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_lr.sv \
  $M/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v $M/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v \
  "${SRC[@]}" "${RS_LIB[@]}" rtl/dsrom_sys/s81_dv/svc_rs/tb_svc_att_cut.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
for s in $SEEDS; do "$O/obj/Vtb_svc_att_cut" +seed=$s > "$O/run_s$s.log" 2>&1 & done; wait
for s in $SEEDS; do echo "== seed $s"; grep -E "^ATT_CUT|^PASS|^FAIL|^CAUGHT|^MISSED" "$O/run_s$s.log"; done
