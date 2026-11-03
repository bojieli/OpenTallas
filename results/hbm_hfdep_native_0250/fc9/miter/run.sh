#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
R=/srv/opentallas-scratch2/claude/codex-hfdep-fc9-miter-vlt-0530
cd "$R"
verilator --binary --timing --assert -Wno-fatal --build-jobs 1 -CFLAGS -O0 --top-module tb --Mdir obj_positive -o positive tb.sv gold/*.sv candidate/hfd_ep_static_fc9.sv > build.log 2>&1
obj_positive/positive > positive.log 2>&1
python3 - <<'PY'
from pathlib import Path
s=Path('candidate/hfd_ep_static_fc9.sv').read_text();old='fault_cause <= {p_st[0], cal_fault, early, lock_lost, bd_cause[6:5], bd_cause[2:0]};';assert old in s
Path('mutant.sv').write_text(s.replace(old,'fault_cause <= {p_st[0], cal_fault, early, lock_lost, bd_cause[6:5], bd_cause[2:0]} ^ 9\'d1;'))
PY
verilator --binary --timing --assert -Wno-fatal --build-jobs 1 -CFLAGS -O0 --top-module tb --Mdir obj_mutant -o mutant tb.sv gold/*.sv mutant.sv > build_mutant.log 2>&1
set +e
obj_mutant/mutant > mutant.log 2>&1
rc=$?
set -e
test "$rc" -ne 0
python3 - <<'PY'
import json,re
from pathlib import Path
p=Path('positive.log').read_text();m=Path('mutant.log').read_text();assert 'HF_FC9_EQ_PASS'in p
checks,diff,active=map(int,re.search(r'HF_FC9 checks=(\d+) diff=(\d+) fault_active=(\d+)',p).groups());assert diff==0 and active>0
z=dict(verdict='FINITE_ACTUAL_SOURCE_PROJECTION_EQ_AND_MUTANT_PASS',cycles=2600,resets=3,checks=checks,diff=diff,actual_fault_active_cycles=active,wrong_retained_fault_bit_mutant_diff=int(re.search(r'diff=(\d+)',m)[1]),SRAMs_each=4,clock_reset_cycles_unchanged=True,scope='All actual selected outputs compared, faultscalar exact, faultcause projected10:5+2:0 only; removedbitconstantsemantics and downstreamOBS136 are separate held proofs',formal_credit=False)
Path('RESULT.json').write_text(json.dumps(z,indent=1)+'\n');print(z)
PY
