#!/bin/bash
set -euo pipefail
cd /tmp/s81-padproof-0825
iverilog -g2012 -s tb -o exact.vvp tb.sv die.v masters.sv ot_fwd_link_stage.sv
vvp exact.vvp | tee exact.log
python3 - <<'PY'
from pathlib import Path
s=Path('die.v').read_text();old=".di({3'b0, n_p0_di})"
# Mutate a logical low bit in the widest mixed-width rebind; use actual generated expression.
import re
m=re.search(r'\.di\(\{(\d+)\x27b0, (p\d+_di)\}\)',s);assert m
# Drop logical bit zero and put zero in its place; output width and spare high bits remain legal.
net=m[2];s=s[:m.start()]+m[0].replace(net,"{"+net+"["+str(int(re.search(r'input \[(\d+):0\] '+net,s)[1]))+":1],1'b0}")+s[m.end():]
Path('mutant.v').write_text(s)
PY
iverilog -g2012 -s tb -o mutant.vvp tb.sv mutant.v masters.sv ot_fwd_link_stage.sv
if vvp mutant.vvp > mutant.log 2>&1; then echo 'MUTANT INCORRECTLY PASSED';exit 1;fi
grep 'logical output mismatch' mutant.log
echo DEDUPE_PAD_MUTANT_REJECTED
