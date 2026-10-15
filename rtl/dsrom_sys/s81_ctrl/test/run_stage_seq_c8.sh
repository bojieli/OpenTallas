#!/bin/bash
# run_stage_seq_c8.sh <src root> <out dir>: die item F4 gate of dsfd_stage_seq_c8 (S81 layer1 sequencer master, engines
# 0..7).  Cases: every stage program whose ops use only ports 0..7 must PASS (NJOB 2 jobs, all ops, no fault); every
# program with an op on port 8..11 must FAULT code 8 (+expect_fault=8).  Mutant OT_SSEQC_MUT_ABSENT (absent-engine
# check off) must FAIL the fault cases.  Prints STAGE_SEQ_C8_GATE PASS|FAIL; exit 0 iff PASS.
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH   # the fleet Verilator (5.050)
SRC=$1; OUT=$2; mkdir -p $OUT
F="$SRC/rtl/lib/ot_reset_sync.sv $SRC/rtl/lib/ot_async_fifo.sv $SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv $SRC/rtl/dsrom_sys/s81_ctrl/dsfd_stage_seq_c.sv $SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_stage_seq_c8.sv"
b() { verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 "$@" $F > $OUT/build_$1.log 2>&1; }
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 --Mdir $OUT/base -o tb $F > $OUT/build_base.log 2>&1 || { echo BUILD_FAIL base; tail $OUT/build_base.log; exit 2; }
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 -DOT_SSEQC_MUT_ABSENT --Mdir $OUT/mut -o tb $F > $OUT/build_mut.log 2>&1 || { echo BUILD_FAIL mut; exit 2; }
# KDALL (s81-die-rtl-bind F4 hop): the kit done waits for the hand-off op -> every program with a hop op must FAIL
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 -DOT_SSEQ_MUT_KDALL --Mdir $OUT/mutk -o tb $F > $OUT/build_mutk.log 2>&1 || { echo BUILD_FAIL mutk; exit 2; }
kh=0; kf=0
IDX=$SRC/results/rtl/s81_ctrl_20261008/programs
np=0; nf=0; bad=0; mf=0; mfn=0
for h in $IDX/hex/*.hex; do
  s=$(basename $h .hex); nops=$(grep -c . $h)
  hi=$(python3 -c "import json;d=json.load(open('$IDX/$s.json'));print(max(o['port'] for o in d['ops']))")
  if python3 -c "import json,sys;d=json.load(open('$IDX/$s.json'));sys.exit(0 if all(o['port'] in (*range(8),12) for o in d['ops']) else 1)"; then
    r=$(timeout 900 $OUT/base/tb +prog=$h +nops=$nops 2>&1 | grep TB_S81); echo "$r" >> $OUT/base.log
    case "$r" in *" PASS") np=$((np+1));; *) bad=$((bad+1));; esac
    if python3 -c "import json,sys;d=json.load(open('$IDX/$s.json'));sys.exit(0 if any(o['port']==7 for o in d['ops']) else 1)"; then
      kh=$((kh+1)); r=$(timeout 900 $OUT/mutk/tb +prog=$h +nops=$nops 2>&1 | grep TB_S81); echo "$r" >> $OUT/mutk.log
      case "$r" in *" PASS") ;; *) kf=$((kf+1));; esac
    fi
  else
    r=$(timeout 900 $OUT/base/tb +prog=$h +nops=$nops +expect_fault=8 2>&1 | grep TB_S81); echo "$r" >> $OUT/base.log
    case "$r" in *" PASS") nf=$((nf+1));; *) bad=$((bad+1));; esac
    r=$(timeout 900 $OUT/mut/tb +prog=$h +nops=$nops +expect_fault=8 2>&1 | grep TB_S81); echo "$r" >> $OUT/mut.log
    mfn=$((mfn+1)); case "$r" in *" PASS") ;; *) mf=$((mf+1));; esac
  fi
done
v=PASS; [ $bad -eq 0 ] && [ $np -gt 0 ] && [ $nf -gt 0 ] && [ $mf -eq $mfn ] && [ $kh -gt 0 ] && [ $kf -gt 0 ] || v=FAIL   # KDALL fails every program whose hop ends after its other ops
echo "STAGE_SEQ_C8_GATE $v programs_exact=$np absent_engine_faults=$nf base_bad=$bad mutant_failed=$mf/$mfn kdall_mutant_failed=$kf/$kh"
[ $v = PASS ] || exit 1

# Port-12 transport on a production-shaped stage: repurpose one existing descriptor, preserving its
# context, predecessors, duration and every other engine op. Compiler VM semantics have their own gate.
python3 - "$IDX" "$OUT/vm.hex" <<'PYVM'
import json, sys
from pathlib import Path
root, out = Path(sys.argv[1]), Path(sys.argv[2])
s = next(p for p in sorted(root.glob('*.json')) if 'ops' in json.loads(p.read_text()) and all(o['port'] < 8 for o in json.loads(p.read_text())['ops']) and any(o['port'] == 1 for o in json.loads(p.read_text())['ops']))
rows = (root / 'hex' / (s.stem + '.hex')).read_text().splitlines()
i = next(i for i,o in enumerate(json.loads(s.read_text())['ops']) if o['port'] == 1)
w = int(rows[i],16); rows[i] = f'{(w & ~(15 << 140)) | (12 << 140):040x}'
out.write_text('\n'.join(rows)+'\n')
PYVM
nops=$(grep -c . "$OUT/vm.hex")
r=$($OUT/base/tb +prog=$OUT/vm.hex +nops=$nops 2>&1 | grep TB_S81); echo "$r" > $OUT/vm.log
case "$r" in *" PASS") ;; *) echo VM_ENGINE12_GATE_FAIL; exit 1;; esac
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-lint --top-module tb_s81_stage_seq_c8 -DOT_SSEQC_MUT_VM_ABSENT --Mdir $OUT/mutvm -o tb $F > $OUT/build_mutvm.log 2>&1 || exit 2
r=$($OUT/mutvm/tb +prog=$OUT/vm.hex +nops=$nops 2>&1 | grep TB_S81); echo "$r" > $OUT/mutvm.log
case "$r" in *" FAIL") echo VM_ENGINE12_GATE_PASS;; *) echo VM_ENGINE12_MUTANT_DID_NOT_FAIL; exit 1;; esac
