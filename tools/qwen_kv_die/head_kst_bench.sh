#!/bin/bash
# KV-KT-E0 2026-11-18: lock-step of the kt-station heads (ot_qkh_head_native_r4*_kst, parameter KT_ST) against their source heads.
# usage: head_kst_bench.sh OUTDIR [FORMS]      (run inside an admitted ot-run unit; one build a form, 5 heads each, ~700 C++
#   files: ot-heavy caps the compile jobs at MEM / 30 GB, so ask for the memory of the jobs you want, e.g. --mem 240 = -j8)
#   forms 0 _s_lk and 1 _ft_s_lk (the two heads of the bound KV die; default "0 1")  2 _s  3 _ft_s  4 r4 (node beat)
#   a form: 7 stimulus seeds default power-up + 7 x 3 random power-up; KT_ST 0 / 2 / 1 and the 14-lane mutant in every run;
#   negative controls on every form: wrong shift 0 / 1 / 3 and the mutant checked against the law must FAIL.
set -u
R=$(cd "$(dirname "$0")/../.." && pwd); OUT=$(mkdir -p "$1" && cd "$1" && pwd); FORMS=${2:-0 1}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
[ -x "$V" ] || V=$(command -v verilator)
J=${KST_JOBS:-32}
S=$R/rtl/qwen_sys/split_20261014; H=$R/rtl/hdc
python3 -I "$R/tools/qwen_kv_die/head_st_rtl.py" --check || { echo "FAIL qkh_head_kst generated RTL stale"; exit 1; }
SRC="$R/rtl/test/qwen_kv_die/tb_qkh_head_kst.sv $S/ot_qkh_head_native_r4_kst.sv $S/ot_qkh_head_kst.sv $S/ot_qkh_head_native_r4_s.sv
 $S/ot_qkh_head_native_r4_s_lk.sv $S/ot_qkh_head_native_r4.sv $S/ot_qkh_head_native_r4_ft.sv
 $S/ot_qkh_head_native.sv $S/ot_qkh_head_native_r3.sv $S/qkh_head_gather_stage.sv $S/qkh_head_stages.sv
 $H/nearhbm/ot_qkh_subtiles.sv $H/nearhbm/ot_qkh_ktree_lk.sv $H/nearhbm/ot_qwen_nearhbm_head_hs.sv $H/nearhbm/ot_qwen_nearhbm_prod.sv
 $H/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv $R/rtl/lib/ot_rst_relay.sv $H/ot_hdc_delay.sv $H/ot_hdc_fp32_add_lat_nr.sv
 $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_fp32_mul_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fastfp.sv"
RES="$OUT/result_forms_$(echo $FORMS | tr ' ' '_').txt"; : > "$RES"; fail=0; npass=0; nneg=0; want_neg=0
run() {  # tag, name, expect (PASS|FAIL), run args
  local tag=$1 name=$2 exp=$3; shift 3
  "$OUT/obj_$tag/Vtb" "$@" > "$OUT/run_${tag}_$name.log" 2>&1 || true
  local line; line=$(grep -E '^(PASS|FAIL) qkh_head_kst' "$OUT/run_${tag}_$name.log" | head -1)
  if [ "${line%% *}" = "$exp" ]; then
    if [ "$exp" = PASS ]; then npass=$((npass+1)); echo "$tag $name: $line" >> "$RES"
    else nneg=$((nneg+1)); echo "$tag $name: negative control caught: $line" >> "$RES"; fi
  else echo "UNEXPECTED $tag $name (want $exp): ${line:-no result line}" | tee -a "$RES"; fail=1; fi
}
for f in $FORMS; do
  tag=f$f
  "$V" --binary -j $J --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qkh_head_kst -DKVD_HEADS=1 -DKVD_Q_FP32=1 \
    -O1 -CFLAGS -O0 --x-initial unique -GFORM=$f -Mdir "$OUT/obj_$tag" -o Vtb $SRC > "$OUT/build_$tag.log" 2>&1 \
    || { tail -30 "$OUT/build_$tag.log"; echo "FAIL build $tag" | tee -a "$RES"; fail=1; continue; }
  for s in 11 23 37 41 59 67 71; do
    run $tag s$s PASS +SEED=$s
    for ps in 1 2 3; do run $tag s${s}_rand$ps PASS +SEED=$s +RAND=1 +verilator+rand+reset+2 +verilator+seed+$((s*7+ps)); done
  done
  for sh in 0 1 3; do run $tag neg_shift$sh FAIL +SEED=11 +SHB=$sh; done
  run $tag neg_shc0 FAIL +SEED=11 +SHC=0
  run $tag neg_mutant FAIL +SEED=11 +CHKM=1
  want_neg=$((want_neg+5))
done
if [ $fail = 0 ] && [ $npass -gt 0 ] && [ $nneg = $want_neg ]; then echo "PASS qkh_head_kst lock-step forms [$FORMS]: $npass runs 0 mismatches, $nneg/$want_neg negative controls caught" | tee -a "$RES"
else echo "FAIL qkh_head_kst lock-step forms [$FORMS]: pass $npass neg $nneg/$want_neg fail $fail" | tee -a "$RES"; exit 1; fi
