#!/usr/bin/env bash
# S-BIND gate: layer-die static sequencer dsfd_stage_seq_static_c8 (engines 0..7 + VM 12). Usage: run_static_c8.sh <outdir>
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd); O=${1:-$R/results/rtl/s81_die_bind_1014/sseq_static_c8}; mkdir -p "$O"; T=$(mktemp -d); cd "$T"
python3 - "$R" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/tools/s81_static_control')
from program import encode_program
w=encode_program([dict(engine=0,arg=0x102938,issue=0,done=3),dict(engine=12,arg=0xfa0312,issue=1,done=4),dict(engine=14,arg=0,issue=6,done=0),dict(engine=15,arg=0,issue=7,done=0)],7,0)
Path('c8.hex').write_text(''.join(f"{x['word']:09x}\n"for x in w['writes']))
PY
S=$R/rtl/dsrom_sys/s81_static_control
SRC="$S/ot_s81_fixed_issue.sv $S/ot_s81_fixed_mailbox.sv $S/dsfd_stage_seq_static_c.sv $S/dsfd_stage_seq_static_c8.sv $S/test/tb_s81_static_c8.sv"
iverilog -g2012 -s tb_s81_static_c8 -o c8 $SRC
for m in 0 1 2; do vvp -n c8 +mode=$m > "$O/mode$m.log" 2>&1; tail -1 "$O/mode$m.log"; done
iverilog -g2012 -DOT_SSEQS_MUT_VM_ABSENT -s tb_s81_static_c8 -o c8m $SRC
if vvp -n c8m +mode=0 > "$O/mut_vm_absent.log" 2>&1 && ! grep -q FATAL "$O/mut_vm_absent.log"; then echo "ERROR: VM-absent mutant escaped"; exit 1; fi
echo "MUT_VM_ABSENT FAIL (expected): $(grep -m1 FATAL "$O/mut_vm_absent.log")"
rm -rf "$T"; echo "S81_STATIC_C8 GATE PASS"
