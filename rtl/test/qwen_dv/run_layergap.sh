#!/usr/bin/env bash
# QW-LAYERGAP 10-20 (TOK.QW.LAYER.4): qfd_dv_slice2 ARF (AR message framer) + RP (RoPE row from the D2D return chain) on
# the 12-slice tb_qfd_dv2 chain, Verilator 5.050 (~40 GB build: fleet only).  One build per VARIANT:
#   pos   -GARF=1 -GRP=1 : calibrate (stn ages must MATCH the committed ones: the framer adds no edge), od/lm --arf PASS,
#                          qk --rope rx PASS, qk --rope rx --mutant rope_late FAIL, qk (stream, regression) PASS
#   off   (no flags)     : od/lm --arf FAIL (framer absent = the old RTL gap), qk --rope rx FAIL (XC sub 1 faults), od PASS
#   mut   -GARF=2 -GRP=2 : od --arf FAIL (last one word early), qk --rope rx FAIL (CROM bank swapped)
#   run_layergap.sh WORK VARIANT        (repository root)
set -u
W=${1:?work}; V=${2:?variant}; mkdir -p "$W"
export PATH=${OT_VERILATOR_BIN:-$HOME/.local/opentallas-tools/verilator-5.050/bin}:$PATH
verilator --version | tee "$W/verilator.txt"
case $V in
  pos) export DV_LOWER_VFLAGS='-GARF=1 -GRP=1';
       RUNS="mat:od:--arf mat:lm:--arf vec:qk:--rope=rx vec:qk:--rope=rx,--mutant=rope_late vec:qk:" ;;
  off) export DV_LOWER_VFLAGS='';
       RUNS="mat:od:--arf mat:lm:--arf vec:qk:--rope=rx mat:od:" ;;
  mut) export DV_LOWER_VFLAGS='-GARF=2 -GRP=2';
       RUNS="mat:od:--arf vec:qk:--rope=rx" ;;
  *) echo "variant $V"; exit 2 ;;
esac
echo "VFLAGS=$DV_LOWER_VFLAGS" | tee "$W/flags.txt"
M=rtl/test/qwen_dv/dv_lower_mat_bench.py; VB=rtl/test/qwen_dv/dv_lower_vec_bench.py
# the build happens in the first (serial) step; calibrate = the measured stn ages on this RTL
python3 $M --work "$W" --calibrate > "$W/calibrate.out" 2>&1; echo "rc=$?" >> "$W/calibrate.out"; cat "$W/calibrate.out"
python3 - "$W/stn_ages.json" results/rtl/qlb_c4b_1018/dv_lower_mat/stn_ages.json <<'PY' | tee -a "$W/calibrate.out"
import json, sys
try:
    m, c = (json.load(open(f)) for f in sys.argv[1:3])
except Exception as e:
    print('AGES MISSING', e); raise SystemExit(0)
k = ('l8_ar', 'ar_hop', 'amax_ami', 'arx_after_amv', 'xc_cc')
print('AGES', 'MATCH' if all(m[x] == c[x] for x in k) else 'DIFFER', {x: (m[x], c[x]) for x in k})
PY
pids=()
for r in $RUNS; do
  b=${r%%:*}; rest=${r#*:}; mode=${rest%%:*}; fl=${rest#*:}; fl=${fl//,/ }; fl=${fl//=/ }
  tag=${b}_${mode}$(echo "$fl" | tr -d ' -' | sed 's/^/_/;s/_$//')
  if [ "$b" = mat ]; then cmd="python3 $M --work $W --run $mode $fl"; else cmd="python3 $VB --work $W --mode $mode $fl"; fi
  ( echo "CMD $cmd"; $cmd; echo "rc=$?" ) > "$W/run_$tag.out" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
for f in "$W"/run_*.out; do echo "== $(basename $f)"; cat "$f"; done > "$W/bench.out"
sha256sum rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/qfd_dv_vm.sv rtl/test/qwen_dv/tb_qfd_dv2.sv $M $VB \
  tools/qwen_layerbench/dv_lower.py tools/qwen_layerbench/dv_lower_mat.py tools/qwen_layerbench/dv_lower_vec.py \
  $(python3 -c "import sys; sys.path.insert(0,'rtl/test/qwen_dv'); import dv_bench2 as B; print(' '.join(B.SRCS2))") \
  | sort -u -k2 > "$W/source.sha256"
cat "$W/bench.out"
rm -rf "$W/obj_n12"
echo CAMPAIGN DONE $V
