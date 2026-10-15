#!/bin/bash
# fill2_cfg7_bench.sh <mode> <out>: one run of the exact cfg7 sequencer lockstep bench (rtl/v41die/test/tb_ot_s81_cfg7_seq.sv,
# cycle lockstep vs the pinned ot_v41_pair_pq_ld_frontend loader, 7 real ot_rom_4096x72_m8 models), for the closure-loop
# bench / failing-mutant pair of the die masters ot_s81_cfg7_seq (PQ 1, as the die binds it) and ot_s81_cfg7_seq_bf (PQ 0).
# modes: pq1 | bf (expect PASS) ; mut_tag (PQ 1 go_tag mutant) | mut_bank_bf (unregistered bank select, BF) (expect FAIL)
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
M=$1; OUT=$2; mkdir -p $OUT
F="rtl/v41die/ot_s81_cfg7_seq.sv physical/dsrom_qx10_parent_context/parent_loader/ot_v41_pair_pq_ld_frontend.sv physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v rtl/v41die/test/tb_ot_s81_cfg7_seq.sv"
case $M in
  pq1) A="-GPQ=1" ;;
  bf) A="-GPQ=0 +define+TB_CFG7_BF" ;;
  mut_tag) A="-GPQ=1 +define+OT_S81_CFG7_MUT_TAG" ;;
  mut_bank_bf) A="-GPQ=0 +define+TB_CFG7_BF +define+OT_S81_CFG7_MUT_BANK" ;;
  *) echo "unknown mode $M"; exit 2 ;;
esac
verilator --binary -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_ot_s81_cfg7_seq $A --Mdir $OUT/obj -o tb $F > $OUT/build.log 2>&1 || { echo "CFG7 BENCH BUILD_FAIL $M"; tail -5 $OUT/build.log; exit 1; }
$OUT/obj/tb > $OUT/run.log 2>&1
if grep -q "^PASS" $OUT/run.log; then grep "^PASS" $OUT/run.log | head -1; echo "CFG7 BENCH PASS $M"; exit 0
else grep -E "Error|stop|fatal" $OUT/run.log | head -2; echo "CFG7 BENCH FAIL $M"; exit 1; fi
