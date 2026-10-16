#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd);O=$(mkdir -p "${1:-/tmp/s81-issuer-status}" && cd "${1:-/tmp/s81-issuer-status}" && pwd)
T=$(mktemp -d);trap 'rm -rf "$T"' EXIT
python3 - "$R" "$T" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/tools/s81_static_control')
from program import encode_program
p=encode_program([dict(engine=0,arg=0x102938,issue=0,done=3),dict(engine=12,arg=0xfa0312,issue=1,done=4),dict(engine=14,arg=0,issue=4,done=0),dict(engine=15,arg=0,issue=5,done=0)],7,0)
Path(sys.argv[2]+'/status.hex').write_text(''.join(f"{x['word']:09x}\n" for x in p['writes']))
PY
S=$R/rtl/dsrom_sys/s81_static_control
SRC="$S/ot_s81_fixed_issue.sv $S/ot_s81_fixed_mailbox.sv $S/dsfd_stage_seq_static_c.sv $S/dsfd_stage_seq_static_c8.sv $S/ot_s81_pq_boot_control.sv $S/dsfd_stage_seq_static_c10.sv $S/test/tb_s81_issuer_status_contract.sv"
cd "$T"
for top in c8 c10; do
 DEF=;if [ "$top" = c8 ];then DEF=-DS81_STATUS_C8;fi
 iverilog -g2012 $DEF -s tb_s81_issuer_status_contract -o sim $SRC
 for m in 0 1;do vvp -n sim +mode=$m > "$O/${top}_mode$m.log";tail -1 "$O/${top}_mode$m.log";done
done
iverilog -g2012 -DS81_STATUS_EARLY_MUTANT -s tb_s81_issuer_status_contract -o mutant $SRC
if vvp -n mutant +mode=1 > "$O/c10_early_mutant.log" 2>&1;then echo 'FAIL early KIT-only consumer escaped';exit 1;fi
grep -q 'fault escaped fixed consumer edge' "$O/c10_early_mutant.log"
echo 'STATUS_CONTRACT PASS: minimum END=last_done+1, fixed sampled success edges c8=210/c10=211; KIT-only mutant FAIL'
