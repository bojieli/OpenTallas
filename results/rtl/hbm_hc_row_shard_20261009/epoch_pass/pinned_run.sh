#!/bin/bash
set -eu
r=/srv/opentallas-scratch/codex/hc-row-shard-r2/epoch_c3b3f94c8
cd "$r/scratch"
cat > harness.cpp <<'CPP'
#include "Vtb_hbm_hc_row_private_epoch.h"
#include "verilated.h"
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){Verilated::commandArgs(argc,argv);Vtb_hbm_hc_row_private_epoch t;while(!Verilated::gotFinish()){t.clk=0;t.eval();t.clk=1;t.eval();}t.final();}
CPP
cd "$r/source"
/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator --cc --exe --build -j 4 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Irtl/common --output-split 20000 --top-module tb_hbm_hc_row_private_epoch -Mdir "$r/scratch/obj" rtl/hdc/hbm/ot_hbm_hc_row_private_epoch.sv rtl/hdc/hbm/ot_hbm_hc_flat_operand_sram.sv rtl/hdc/hbm/ot_hbm_hc_row_operand_epoch.sv rtl/model/ot_hbm_hc_operand_sram_sim.sv rtl/common/ot_secded.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/test/tb_hbm_hc_row_private_epoch.sv "$r/scratch/harness.cpp" > "$r/scratch/build.log" 2>&1
cd "$r/scratch"
./obj/Vtb_hbm_hc_row_private_epoch > exact.log 2>&1
set +e
./obj/Vtb_hbm_hc_row_private_epoch +MUTANT > negative.log 2>&1
status=$?
set -e
test "$status" -ne 0
for arm in BADLEASE WRONGFN LATEFN; do
 ./obj/Vtb_hbm_hc_row_private_epoch +"$arm" > "$arm.log" 2>&1
 if grep -q Fatal "$arm.log"; then exit 1; fi
done
grep -q HC_FN_EPOCH_REJECTED WRONGFN.log
grep -q 'HC_FN_EPOCH_REJECTED late=1 committed=0' LATEFN.log
printf 'HC_FULLSHAPE_FN_EPOCH_GATE_PASS negative_rc=%s\n' "$status"
