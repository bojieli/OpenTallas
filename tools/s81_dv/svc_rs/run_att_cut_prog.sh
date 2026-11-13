#!/usr/bin/env bash
# CUT-BENCH-1 (HARD-S81-SVC-1, 11-13): PROGRAMME-DRIVEN dsdv_svc_att vs dsdv_svc_att_cut (+ CUTMUT 2, 3) lock-step
# (tb_svc_att_cut_prog: legal CFG / OWN_ROW / WIN_LOAD / SEL_IDS / ROWS / ATTN_Q / SMJ / PV / GO programme, H 8 two passes,
# PC model, host writes, warm reset), seeds $SEEDS, extra plusargs $ARGS.  LINT=1: lint only.
# Run from the repo root:  run_att_cut_prog.sh OUT_DIR
set -euo pipefail
O=$(realpath -m "$1"); SEEDS=${SEEDS:-"1 2 3"}; ARGS=${ARGS:-}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
source tools/s81_dv/svc_rs/rs_files.sh
mkdir -p "$O"
A=rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
SRC=(); for f in "${RS_SRC[@]}"; do [ "$f" = "$D/dsdv_svc_rs.sv" ] || SRC+=("$f"); done
printf "%s\n" "${SRC[@]}" | grep -qx "$A" || SRC+=("$A")
SRC+=(rtl/hdc/v41x/ot_s81c_attn_hcore.sv rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv)
M=physical/asap7_memory_macros_v2
FL=(-Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --unroll-count 16 --unroll-limit 131072 -I"$D"
  -DOT_SVC_ALLQ -DOT_SVC_H8 -DOT_SVC_H8_REUSE_RT2 -DOT_ATTN_HCORE -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DSU_SMU_T
  -DOT_SVC_ATT_MEM_MACRO "${RS_DEF[@]}" rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_cut.sv
  rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_la.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_lr.sv
  $M/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v $M/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v
  "${SRC[@]}" "${RS_LIB[@]}" rtl/dsrom_sys/s81_dv/svc_rs/tb_svc_att_cut_prog.sv)
if [ "${LINT:-0}" = 1 ]; then
  "$VL" --lint-only --timing --top-module tb_svc_att_cut_prog "${FL[@]}" > "$O/lint.log" 2>&1; rc=$?
  grep -E "%Error" "$O/lint.log" | head -40; echo "LINT_RC $rc"; exit $rc
fi
if [ ! -x "$O/obj/Vtb_svc_att_cut_prog" ]; then
  /usr/bin/time -v "$VL" --binary --top-module tb_svc_att_cut_prog -Mdir "$O/obj" -j 16 -CFLAGS -O1 "${FL[@]}" > "$O/build.log" 2>&1 \
    || { tail -30 "$O/build.log"; exit 1; }
fi
for s in $SEEDS; do "$O/obj/Vtb_svc_att_cut_prog" +seed=$s $ARGS > "$O/run_s$s.log" 2>&1 & done; wait
for s in $SEEDS; do echo "== seed $s"; grep -E "^PROG|^CUT_PROG|^FIRST_MISMATCH|^  |^PASS|^FAIL|^CAUGHT|^MISSED|^TIMEOUT" "$O/run_s$s.log"; done
