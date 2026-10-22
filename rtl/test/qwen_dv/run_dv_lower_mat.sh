#!/usr/bin/env bash
# QLB-C4b/3b 10-18: dv_lower_mat bench campaign on ONE tb_qfd_dv2 N 12 build (Verilator 5.050, ~40 GB build: fleet only,
# ot-run --mem 160).  Calibrate first (stn_ages.json), then every run and mutant in parallel on the same executable.
#   run_dv_lower_mat.sh WORK [AGES]     (repository root; AGES default = the calibrated WORK/stn_ages.json)
set -u
W=${1:?work dir}; mkdir -p "$W"
export PATH=${OT_VERILATOR_BIN:-$HOME/.local/opentallas-tools/verilator-5.050/bin}:$PATH
verilator --version | tee "$W/verilator.txt"
B=rtl/test/qwen_dv/dv_lower_mat_bench.py
python3 $B --work "$W" --calibrate > "$W/calibrate.out" 2>&1; echo "rc=$?" >> "$W/calibrate.out"; cat "$W/calibrate.out"
AG=${2:-$W/stn_ages.json}
[ -f "$AG" ] || { echo "no ages"; exit 1; }
python3 - "$W/stn_ages.json" "$AG" <<'PY' | tee -a "$W/calibrate.out"
import json, sys
m, c = (json.load(open(f)) for f in sys.argv[1:3])
k = ('l8_ar', 'ar_hop', 'amax_ami', 'arx_after_amv', 'xc_cc')
print('AGES', 'MATCH' if all(m[x] == c[x] for x in k) else 'DIFFER', {x: (m[x], c[x]) for x in k})
PY
pids=()
for rm in qkv: gu: od: lm: emb: qkv:sbase1 gu:sbase1 od:nostagger od:xc_bc lm:amax_local emb:emb_late; do
  r=${rm%%:*}; m=${rm#*:}; tag=${r}_${m:-m0}
  ( python3 $B --work "$W" --run "$r" ${m:+--mutant $m} --ages "$AG" > "$W/run_$tag.out" 2>&1; echo "rc=$?" >> "$W/run_$tag.out" ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
for f in "$W"/run_*.out; do echo "== $(basename $f)"; cat "$f"; done > "$W/bench.out"
sha256sum tools/qwen_layerbench/dv_lower_mat.py tools/qwen_layerbench/dv_lower.py $B rtl/test/qwen_dv/dv_lower_bench.py \
  rtl/test/qwen_dv/dv_bench.py rtl/test/qwen_dv/dv_bench2.py rtl/test/qwen_dv/main2.cpp rtl/test/qwen_dv/tb_qfd_dv2.sv \
  $(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as B; print(' '.join(B.SRCS2))") \
  tools/hdc_golden.py results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/token_source_plan.json \
  results/arch/qwen_split_compute_1014/dieplan2_1016/dv2r8f7r_qdv_p2462.json \
  results/rtl/qlb_gen_1018/dv2f14bq/relay_stages_compute.json results/rtl/qlb_c4_1018/dv_lower/slice_ages.json \
  results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex "$AG" | sort -u -k2 > "$W/source.sha256"
cat "$W/bench.out"
rm -rf "$W/obj_n12"
echo CAMPAIGN DONE
