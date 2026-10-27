#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for n in 2 4; do
 yosys -Q -T -p "read_verilog -formal -sv native.sv capture_miter.sv; chparam -set NPC $n capture_miter; hierarchy -top capture_miter; proc; flatten; opt; sat -set-def-inputs -set-init-zero -seq 2 -tempinduct -prove mismatch 0 -verify" > "sat_n${n}.log" 2>&1
 grep 'SUCCESS' "sat_n${n}.log"
 if yosys -Q -T -p "read_verilog -formal -sv native.sv capture_miter.sv; chparam -set NPC $n -set MUT 1 capture_miter; hierarchy -top capture_miter; proc; flatten; opt; sat -set-def-inputs -set-init-zero -seq 8 -prove mismatch 0 -verify" > "mut_n${n}.log" 2>&1;then echo "MUTANT_SURVIVED NPC$n";exit 1;fi
 grep -E 'proof did fail|FAIL' "mut_n${n}.log"
done
iverilog -g2012 -DMUT=0 -s tb_hbm_svc_vmdel_lane_n_lockstep -o native_sim native_tb.sv native.sv old_split.sv sram.v > native_compile.log 2>&1
vvp -n native_sim > native_context.log 2>&1
grep 'VMDEL_N_LOCKSTEP PASS' native_context.log
printf '%s\n' 'CAPTURE_PROOF_PASS NPC2+4 unbounded-induction/256bits, selector-mutants-caught, native-context-PASS' > done
cat done
