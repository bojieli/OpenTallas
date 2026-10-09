#!/usr/bin/env bash
set -uo pipefail
cd /srv/opentallas-scratch/claude/emb-hub-sram-r1
mkdir -p logs
src=rtl/qwen_sys/emb_hbm_20261008/ot_qfd_hub_sram_ingress.sv
macro=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
bench=results/arch/emb_hbm_20261008/takeover/hub_sram_gate/tb_ingress.sv
iverilog -g2012 -s tb_ingress -o ingress.vvp "$src" "$macro" "$bench" >logs/compile.log 2>&1 || exit 1
vvp ingress.vvp +MODE=0 >logs/positive.log 2>&1; echo "$?" >logs/positive.rc
vvp ingress.vvp +MODE=2 >logs/overflow.log 2>&1; echo "$?" >logs/overflow.rc
vvp ingress.vvp +MODE=3 >logs/ue.log 2>&1; echo "$?" >logs/ue.rc
vvp ingress.vvp +MODE=4 >logs/payload_mutant.log 2>&1; echo "$?" >logs/payload_mutant.rc
iverilog -g2012 -DEARLY_MUT -s tb_ingress -o early.vvp "$src" "$macro" "$bench" >logs/early_compile.log 2>&1 || exit 1
vvp early.vvp +MODE=0 >logs/early_credit_mutant.log 2>&1; echo "$?" >logs/early_credit_mutant.rc
cat logs/*.rc logs/*.log
