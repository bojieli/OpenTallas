#!/usr/bin/env bash
# S-DIE-NETLIST gate: layer-die static sequencer dsfd_stage_seq_static_c10 (engines 0..7 + Engram MIX4 10 + VM 12 + PQ 13).
# Usage: run_static_c10.sh <outdir>.  Programs {0,12} (the c8 fixture) and {10,13} (MIX4 + PQ faces), modes 0/1/2 each;
# mutants: engine 10 masked (OT_SSEQS_MUT_ENG_ABSENT) and engine 13 masked (OT_SSEQS_MUT_PQ_ABSENT) must fault.
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd); O=${1:-$R/results/rtl/s81_die_bind_1014/sseq_static_c10}; mkdir -p "$O"; O=$(cd "$O" && pwd); T=$(mktemp -d); cd "$T"
S=$R/rtl/dsrom_sys/s81_static_control
SRC="$S/ot_s81_fixed_issue.sv $S/ot_s81_fixed_mailbox.sv $S/dsfd_stage_seq_static_c.sv $S/ot_s81_pq_boot_control.sv $S/dsfd_stage_seq_static_c10.sv $S/test/tb_s81_static_c10.sv"
iverilog -g2012 -s tb_s81_static_c10 -o c10 $SRC
iverilog -g2012 -DOT_SSEQS_MUT_ENG_ABSENT -s tb_s81_static_c10 -o c10me $SRC
iverilog -g2012 -DOT_SSEQS_MUT_PQ_ABSENT -s tb_s81_static_c10 -o c10mp $SRC
for p in "0 12" "10 13"; do
  set -- $p
  python3 - "$R" "$1" "$2" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/tools/s81_static_control')
from program import encode_program
e0,e1=int(sys.argv[2]),int(sys.argv[3])
w=encode_program([dict(engine=e0,arg=0x102938,issue=0,done=3),dict(engine=e1,arg=0xfa0312,issue=1,done=4),dict(engine=14,arg=0,issue=6,done=0),dict(engine=15,arg=0,issue=7,done=0)],7,0)
Path('c10.hex').write_text(''.join(f"{x['word']:09x}\n"for x in w['writes']))
PY
  for m in 0 1 2; do vvp -n c10 +mode=$m +e0=$1 +e1=$2 > "$O/e$1_$2_mode$m.log" 2>&1; tail -1 "$O/e$1_$2_mode$m.log"; grep -q "S81_STATIC_C10 mode=$m" "$O/e$1_$2_mode$m.log"; done
done
for mu in me:ENG_ABSENT:10 mp:PQ_ABSENT:13; do
  IFS=: read b n e <<< "$mu"
  if vvp -n c10$b +mode=0 +e0=10 +e1=13 > "$O/mut_${n,,}.log" 2>&1 && ! grep -q FATAL "$O/mut_${n,,}.log"; then echo "ERROR: $n mutant escaped"; exit 1; fi
  echo "MUT_$n FAIL (expected): $(grep -m1 'FATAL\|fatal\|corrupt\|lost' "$O/mut_${n,,}.log")"
done
rm -rf "$T"; echo "S81_STATIC_C10 GATE PASS"
