#!/usr/bin/env bash
# DIE-S81-85 form A (3): dsdv_svc_att flop vs macro vs macro+MUT lock-step (tb_svc_att_mem), seeds $SEEDS.  Run from the repo root.
set -euo pipefail
O=$(realpath -m "$1"); SEEDS=${SEEDS:-"1 2"}; NCYC=${NCYC:-200000}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
source tools/s81_dv/svc_rs/rs_files.sh
mkdir -p "$O/src"
A=rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
mk() {  # $1 suffix, $2.. defines
  local s=$1; shift; local f="$O/src/dsdv_svc_att_$s.sv"
  { for d in "$@"; do echo "\`define $d"; done
    sed -E "s/^module dsdv_svc_att #\(/module dsdv_svc_att_$s #(/" "$A"
    for d in "$@"; do echo "\`undef $d"; done; } > "$f"
  grep -q "^module dsdv_svc_att_$s " "$f" || { echo "rename failed $s"; exit 1; }
}
mk f
mk m OT_SVC_ATT_MEM_MACRO
mk mm OT_SVC_ATT_MEM_MACRO OT_SVC_ATT_MEM_MACRO_MUT
SRC=(); for f in "${RS_SRC[@]}"; do [ "$f" = "$A" ] || [ "$f" = "$D/dsdv_svc_rs.sv" ] || SRC+=("$f"); done
SRC+=(rtl/hdc/v41x/ot_s81c_attn_hcore.sv rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv)
M=physical/asap7_memory_macros_v2
"$VL" --binary --top-module tb_svc_att_mem -Mdir "$O/obj" -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  --unroll-count 16 --unroll-limit 131072 -CFLAGS -O1 -I"$D" -DOT_SVC_ALLQ -DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2 -DOT_ATTN_HCORE \
  -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DSU_SMU_T -DOT_SVC_MEM_COV -GNCYC=$NCYC \
  "${RS_DEF[@]}" "$O/src/dsdv_svc_att_f.sv" "$O/src/dsdv_svc_att_m.sv" "$O/src/dsdv_svc_att_mm.sv" \
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_la.sv \
  $M/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v $M/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v \
  "${SRC[@]}" "${RS_LIB[@]}" rtl/dsrom_sys/s81_dv/svc_rs/tb_svc_att_mem.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
for s in $SEEDS; do "$O/obj/Vtb_svc_att_mem" +seed=$s > "$O/run_s$s.log" 2>&1 & done; wait
for s in $SEEDS; do echo "== seed $s"; grep -E "^ATT_MEM|^PASS|^FAIL|^CAUGHT|^MISSED" "$O/run_s$s.log"
  grep -h MEM_COV "$O/run_s$s.log" | sed -E 's/.*(u_m|u_mm)\./\1./' | sort | head -40; done
