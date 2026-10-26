#!/bin/bash
# cfg7_bfp_bench.sh <mode> <out>: exact lockstep gate of ot_s81_cfg7_seq_bfp (rtl/v41die/test/tb_ot_s81_cfg7_seq_bfp.sv).
# modes: base | pr (PINREG 1 / LAYOUT 1) expect PASS; mut_row | pr_mut_row | pr_mut_spdl expect FAIL
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
M=$1; OUT=$2; mkdir -p $OUT
F="rtl/v41die/ot_s81_cfg7_seq.sv rtl/v41die/ot_s81_cfg7_seq_bfp.sv rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv rtl/lib/ot_rst_relay.sv rtl/v41die/test/tb_ot_s81_cfg7_seq_bfp.sv"
case $M in
  base) A="" ;;
  pr) A="+define+TB_BFP_PINREG" ;;
  pr_empty) A="+define+TB_BFP_PINREG +define+TB_BFP_EMPTY" ;;
  pr_empty_mut_fault) A="+define+TB_BFP_PINREG +define+TB_BFP_EMPTY +define+OT_S81_BF_PROG_MUT_EMPTY_FAULT" ;;
  mut_row) A="+define+OT_S81_CFG7_BFP_MUT_ROW" ;;
  pr_mut_row) A="+define+TB_BFP_PINREG +define+OT_S81_CFG7_BFP_MUT_ROW" ;;
  pr_mut_spdl) A="+define+TB_BFP_PINREG +define+OT_S81_CFG7_BFP_MUT_SPDL" ;;
  *) echo "unknown mode $M"; exit 2 ;;
esac
verilator --binary -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_ot_s81_cfg7_seq_bfp $A --Mdir $OUT/obj -o tb $F > $OUT/build.log 2>&1 || { echo "BFP BENCH BUILD_FAIL $M"; tail -5 $OUT/build.log; exit 1; }
$OUT/obj/tb > $OUT/run.log 2>&1
if grep -q "^PASS" $OUT/run.log; then grep "^PASS" $OUT/run.log | head -1; echo "BFP BENCH PASS $M"; exit 0
else grep -E "MISMATCH|Error|fatal" $OUT/run.log | head -2; echo "BFP BENCH FAIL $M"; exit 1; fi
