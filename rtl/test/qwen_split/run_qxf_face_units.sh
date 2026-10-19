#!/bin/bash
# QXF-FACE 2026-10-18 (TOKEN-XDIE-QWEN F3): unit slice benches of the max(P0, P1, R) join-age law, Verilator 5.050.
#   pvfin: tb_qkd_pv_fin_s (qkd_pv_fin_s lockstep vs the reference ot_qwen_tp8_pv_join16_static_cal slices)
#   face : tb_qkd_attn_result_face_s (real programme + service root + qkd_attn_result_face_s)
# usage (repository root, on the fleet via ot-run): run_qxf_face_units.sh OUTDIR
# One line per case "<name> expect=<PASS|FAIL> got=<PASS|FAIL> -> OK | UNEXPECTED"; exit 0 only if every case is OK.
# Fail regex (mutants): pvfin '^FAIL [1-9][0-9]* mismatches|^MISMATCH|cmd [0-9]+ fault'; face 'went undetected|%Error|fault=1'.
set -u
OUT=$1; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/qwen_sys/split_20261014
PVF=("$S/qkd_pv_fin_s.sv" rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static_cal_gen.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
     rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/test/qwen_split/tb_qkd_pv_fin_s.sv)
FACE=("$S/qkd_native_attention_programme.sv" "$S/qkd_native_attention_static_ctl.sv" "$S/qkd_native_attention_record.sv"
      "$S/qkd_native59_command_guard.sv" "$S/qkd_native59_descriptor_producer.sv" "$S/qkd_attn_service_root.sv"
      "$S/qkd_attn_result_face_s.sv" rtl/test/qwen_split/tb_qkd_attn_result_face_s.sv)
sha256sum "${PVF[@]}" "${FACE[@]}" "$0" > "$OUT/source.sha256"
VF=(--binary --timing -j "${JOBS:-4}" -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN)
build() {  # name top gflags sources...
  local n=$1 top=$2 g=$3; shift 3
  $V "${VF[@]}" --top-module "$top" $g --Mdir "$OUT/obj_$n" "$@" > "$OUT/build_$n.log" 2>&1 || { echo "BUILD_FAIL $n"; grep -m5 %Error "$OUT/build_$n.log"; return 1; }
}
res=()
case_() {  # name expect binary plusargs regex_pass
  local n=$1 exp=$2 bin=$3 pa=$4 rx=$5
  "$bin" $pa > "$OUT/$n.log" 2>&1; local rc=$?
  local got=FAIL; [ $rc -eq 0 ] && grep -qE "$rx" "$OUT/$n.log" && got=PASS
  local line="$n expect=$exp got=$got -> $([ $got = $exp ] && echo OK || echo UNEXPECTED) | $(grep -E 'PASS|FAIL|MISMATCH|undetected|fault=' "$OUT/$n.log" | head -2 | tr '\n' ' ')"
  echo "$line"; res+=("$line")
}
build pv0 tb_qkd_pv_fin_s "-GMUT=0" "${PVF[@]}" &
build pv3 tb_qkd_pv_fin_s "-GMUT=3" "${PVF[@]}" &
build pv1 tb_qkd_pv_fin_s "-GMUT=1" "${PVF[@]}" &
build f0 tb_qkd_attn_result_face_s "-GMUT=0 -GR_P=32" "${FACE[@]}" &
build f600 tb_qkd_attn_result_face_s "-GMUT=0 -GR_P=600" "${FACE[@]}" &
build f4 tb_qkd_attn_result_face_s "-GMUT=4 -GR_P=600" "${FACE[@]}" &
build f4s tb_qkd_attn_result_face_s "-GMUT=4 -GR_P=32" "${FACE[@]}" &
wait
P=Vtb_qkd_pv_fin_s; F=Vtb_qkd_attn_result_face_s
case_ pvfin_lockstep_R_le_pairs PASS "$OUT/obj_pv0/$P" "+SEED=7 +N=40" '^PASS STRETCH=0'
case_ pvfin_lockstep_stretch PASS "$OUT/obj_pv0/$P" "+SEED=9 +N=48 +STRETCH=1" '^PASS STRETCH=1'
case_ pvfin_mut3_noR_stretch FAIL "$OUT/obj_pv3/$P" "+SEED=9 +N=6 +STRETCH=1" '^PASS STRETCH=1'
case_ pvfin_mut3_noR_R_le_pairs PASS "$OUT/obj_pv3/$P" "+SEED=7 +N=12" '^PASS STRETCH=0'
case_ pvfin_mut1_head FAIL "$OUT/obj_pv1/$P" "+SEED=11 +N=40" '^PASS STRETCH=0'
for g in 1 2 3; do case_ pvfin_neg$g PASS "$OUT/obj_pv0/$P" "+SEED=5 +N=6 +NEG=$g" 'DUT fault raised \(expected\)'; done
for m in 0 1 2 3 4 5 6 7; do case_ face_R32_mode$m PASS "$OUT/obj_f0/$F" "+MODE=$m" '^PASS R32'; done
for m in 0 1 5 7; do case_ face_R600_mode$m PASS "$OUT/obj_f600/$F" "+MODE=$m" '^PASS R600'; done
case_ face_mut4_noR_R600 FAIL "$OUT/obj_f4/$F" "+MODE=0" '^PASS R600'
case_ face_mut4_noR_R32 FAIL "$OUT/obj_f4s/$F" "+MODE=0" '^PASS R32'
rm -rf "$OUT"/obj_*
printf '%s\n' "${res[@]}" > "$OUT/SUMMARY.txt"
! grep -q "UNEXPECTED" "$OUT/SUMMARY.txt" && [ ${#res[@]} -eq 22 ]
