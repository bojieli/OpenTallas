#!/bin/bash
set -u
cd "$(dirname "$0")"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version > verilator.version
for c in tt ff; do
 "$VL" --binary --timing --top-module tb -Wno-fatal --Mdir obj_$c -j 2 tb_$c.sv qfd_link_slots.sv qfd_fwd_lane.sv ot_qwen_rst_rep.sv selected_masters.sv qfd_land8.sv > build_$c.log 2>&1 || exit $?
 obj_$c/Vtb +mode=0 > epoch_${c}_measure.log 2>&1 || exit $?
 K=$(python3 -c 'import re,sys; t=open(sys.argv[1]).read();m=re.search(r"formula=(\d+)",t);assert m;print(m[1])' epoch_${c}_measure.log) || exit $?
 obj_$c/Vtb +mode=1 +K=$K > epoch_${c}_pass.log 2>&1 || exit $?
 BAD=$((K ^ 8))
 obj_$c/Vtb +mode=1 +K=$BAD > epoch_${c}_mut_k3.log 2>&1
 rc=$?
 if [ "$rc" = 0 ]; then echo "UNCAUGHT_K3_MUTANT $c"; exit 2; fi
 python3 -c 'import re,sys; t=open(sys.argv[1]).read();m=re.search(r"errors=(\d+) faults=(\d+)",t);assert m and (int(m[1])>0 or int(m[2])>0), "mutant only failed configuration guard"' epoch_${c}_mut_k3.log || exit $?
 echo "EPOCH_CORNER $c PASS K=$K K3_MUTANT_REJECTED"
done
python3 - <<'PY'
from pathlib import Path
import re
ks=[]
for c in ['tt','ff']:
 s=Path(f'epoch_{c}_measure.log').read_text();m=re.search(r'formula=(\d+)',s);assert m;ks.append(int(m[1]))
assert ks[0]==ks[1],f'NO_COMMON_IMMUTABLE_K TTFF={ks}'
print(f'COMMON_IMMUTABLE_K={ks[0]} RTL_COLD_CASES_ONLY_NOT_NATIVE_SIGNOFF')
PY
