#!/bin/bash
# run_stage_seq_c8.sh <src root> <out dir>: die item F4 gate of dsfd_stage_seq_c8 (S81 layer1 sequencer master, engines
# 0..7).  Cases: every stage program whose ops use only ports 0..7 must PASS (NJOB 2 jobs, all ops, no fault); every
# program with an op on port 8..11 must FAULT code 8 (+expect_fault=8).  Mutant OT_SSEQC_MUT_ABSENT (absent-engine
# check off) must FAIL the fault cases.  Prints STAGE_SEQ_C8_GATE PASS|FAIL; exit 0 iff PASS.
set -u
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/lib/ot_reset_sync.sv $SRC/rtl/lib/ot_async_fifo.sv $SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv $SRC/rtl/dsrom_sys/s81_ctrl/dsfd_stage_seq_c.sv $SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_stage_seq_c8.sv"
b() { verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 "$@" $F > $OUT/build_$1.log 2>&1; }
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 --Mdir $OUT/base -o tb $F > $OUT/build_base.log 2>&1 || { echo BUILD_FAIL base; tail $OUT/build_base.log; exit 2; }
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 -DOT_SSEQC_MUT_ABSENT --Mdir $OUT/mut -o tb $F > $OUT/build_mut.log 2>&1 || { echo BUILD_FAIL mut; exit 2; }
IDX=$SRC/results/rtl/s81_ctrl_20261008/programs
np=0; nf=0; bad=0; mf=0; mfn=0
for h in $IDX/hex/*.hex; do
  s=$(basename $h .hex); nops=$(grep -c . $h)
  hi=$(python3 -c "import json;d=json.load(open('$IDX/$s.json'));print(max(o['port'] for o in d['ops']))")
  if [ $hi -le 7 ]; then
    r=$(timeout 900 $OUT/base/tb +prog=$h +nops=$nops 2>&1 | grep TB_S81); echo "$r" >> $OUT/base.log
    case "$r" in *" PASS") np=$((np+1));; *) bad=$((bad+1));; esac
  else
    r=$(timeout 900 $OUT/base/tb +prog=$h +nops=$nops +expect_fault=8 2>&1 | grep TB_S81); echo "$r" >> $OUT/base.log
    case "$r" in *" PASS") nf=$((nf+1));; *) bad=$((bad+1));; esac
    r=$(timeout 900 $OUT/mut/tb +prog=$h +nops=$nops +expect_fault=8 2>&1 | grep TB_S81); echo "$r" >> $OUT/mut.log
    mfn=$((mfn+1)); case "$r" in *" PASS") ;; *) mf=$((mf+1));; esac
  fi
done
v=PASS; [ $bad -eq 0 ] && [ $np -gt 0 ] && [ $nf -gt 0 ] && [ $mf -eq $mfn ] || v=FAIL
echo "STAGE_SEQ_C8_GATE $v programs_exact=$np absent_engine_faults=$nf base_bad=$bad mutant_failed=$mf/$mfn"
[ $v = PASS ]
