#!/bin/bash
# Fleet runner: finite FF WTN1 witness controller + typed SU observer, Verilator 5.050.
set -uo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > verilator.version
python3 -I src/tools/qwen_layerbench/typed_witness_control_vectors.py --pw src/model_pw.hex --out vec > vectors.log || exit 2
SRCS="src/rtl/qwen_dv/qfd_dv_typed_su_observer.sv src/rtl/qwen_dv/qfd_dv_typed_witness_control.sv src/rtl/test/qwen_dv/tb_qwen_typed_witness_control.sv"
for en in 1 0; do
 "$V" --binary --timing -j 8 -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-fatal --top-module tb_qwen_typed_witness_control -GEN=$en -GSAFE=1 -Mdir obj$en $SRCS > build$en.log 2>&1 || { echo BUILD_FAIL $en; exit 3; }
done
ok=1
obj1/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt > nominal.log 2>&1
grep -q 'TWC_RESULT_CLEAN' nominal.log && grep -q 'completions=65 retired=5 starts=5' nominal.log && grep -q 'ready_seen=1' nominal.log && ! grep -q -E 'ORDER_ERROR|RETIRE_EARLY' nominal.log || { echo NOMINAL_FAIL; ok=0; }
obj0/Vtb_qwen_typed_witness_control +STIM=vec/stim_nominal.txt > legacy.log 2>&1
grep -q 'en=0 fault=0 obs_fault=0 ready_seen=0 ready_end=0 completions=0' legacy.log || { echo LEGACY_FAIL; ok=0; }
for m in $(python3 -I -c "import json;print(' '.join(json.load(open('vec/vectors.json'))['mutants']))"); do
 obj1/Vtb_qwen_typed_witness_control +STIM=vec/stim_$m.txt > mut_$m.log 2>&1
 if grep -q TWC_RESULT_FAULT mut_$m.log; then echo "MUT $m FAIL_AS_EXPECTED $(grep -o 'first_fault=[0-9-]*' mut_$m.log)"; else echo "MUT $m ESCAPED"; ok=0; fi
done | tee mutants.log
grep -q ESCAPED mutants.log && ok=0
grep -E 'Warning' build1.log | sed 's/^%//' | sort | uniq -c | sort -rn | head -20 > lint_summary.log
if [ $ok = 1 ]; then echo TYPED_WITNESS_CONTROL_PASS; else echo TYPED_WITNESS_CONTROL_FAIL; exit 1; fi
