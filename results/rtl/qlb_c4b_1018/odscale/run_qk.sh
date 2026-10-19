#!/bin/bash
set -euo pipefail
R=$PWD
export QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8
export OT_GOLD_ROOT="$R/src"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
for layer in 0 1; do
 python3 src/tools/qwen_layerbench/dv_layer_fixture_qk.py tp8stages --img "$R/img/L{layer}/die{die}" --tp8gold "$R/gold/P8191/P8191" --layer "$layer" --out "$R/fx_qk"
done
for case in L0_qk L1_qk MUT_L0_qk_ropesign; do
 layer=0
 [[ $case == L1_qk ]] && layer=1
 d="$R/runs_qk/$case"
 mkdir -p "$d"
 ln -s "$R/bin" "$d/obj_n12"
 args=()
 expected=0
 if [[ $case == MUT* ]]; then args=(--mutant ropesign); expected=1; fi
 set +e
 python3 src/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode qk --fixture "$R/fx_qk/L${layer}_qk_tp8.npz" --work "$d" "${args[@]}" > "$d/bench.out" 2>&1
 rc=$?
 set -e
 echo "rc=$rc" >> "$d/bench.out"
 head -1 "$d/bench.out"
 test "$rc" -eq "$expected"
done
