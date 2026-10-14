#!/bin/bash
# run_cfg7_seq_gate.sh <src root> <out dir>: exact gate of the pair configuration sequencer die masters (lockstep vs
# ot_v41_pair_pq_ld_frontend): ot_s81_cfg7_seq PQ 0 / PQ 1 and the BF pair master ot_s81_cfg7_seq_bf (PQ 0), each PASS;
# mutants STRIDE / BANK (every master) and TAG / NOFAULT / NOHOLD (PQ 1) must FAIL.
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH   # the fleet Verilator (5.050), not the host default
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/v41die/ot_s81_cfg7_seq.sv $SRC/physical/dsrom_qx10_parent_context/parent_loader/ot_v41_pair_pq_ld_frontend.sv $SRC/physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v $SRC/rtl/v41die/test/tb_ot_s81_cfg7_seq.sv"
v=PASS
run() { l=$1; want=$2; shift 2
  verilator --binary -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_ot_s81_cfg7_seq "$@" --Mdir $OUT/$l -o tb $F > $OUT/build_$l.log 2>&1 || { echo "$l BUILD_FAIL"; v=FAIL; return; }
  $OUT/$l/tb > $OUT/run_$l.log 2>&1
  if grep -q "^PASS" $OUT/run_$l.log; then got=PASS; else got=FAIL; fi
  echo "$l $got (want $want): $(grep -E '^PASS|fatal|Error|FAIL' $OUT/run_$l.log | head -1 | cut -c1-160)"
  [ $got = $want ] || v=FAIL
}
run pq0 PASS -GPQ=0
run pq1 PASS -GPQ=1
run bf PASS -GPQ=0 +define+TB_CFG7_BF
run bf_stride FAIL -GPQ=0 +define+TB_CFG7_BF +define+OT_S81_CFG7_MUT_STRIDE
run bf_bank FAIL -GPQ=0 +define+TB_CFG7_BF +define+OT_S81_CFG7_MUT_BANK
run pq1_tag FAIL -GPQ=1 +define+OT_S81_CFG7_MUT_TAG
run pq1_nohold FAIL -GPQ=1 +define+OT_S81_CFG7_MUT_NOHOLD
echo "CFG7_SEQ_GATE $v"; [ $v = PASS ]
