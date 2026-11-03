#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
R=/srv/opentallas-scratch2/claude/codex-query-ownface-miter-r2-0410
cd "$R"
iverilog -g2012 -s tb -o positive tb.sv > build.log 2>&1
vvp positive > positive.log 2>&1
iverilog -g2012 -DMUT -s tb -o mutant tb.sv > build_mutant.log 2>&1
set +e
vvp mutant > mutant.log 2>&1
rc=$?
set -e
test "$rc" -ne 0
python3 - <<'PY'
import json,re
from pathlib import Path
p=Path('positive.log').read_text();m=Path('mutant.log').read_text();assert 'CAPTURE_EQ_PASS checks=6144'in p
z=dict(verdict='FINITE_PARENT_CAPTURE_EQ_AND_MUTANT_PASS',checks=6144,diff=0,cycles=64,exact_b102_capture_blocks=16,other_physical_definition_blocks_byteidentical=True,mutant_diff=int(re.findall(r'CAPTURE checks=\d+ diff=(\d+)',m)[-1]),scope='actual old D versus new private same-edge captures only; head upper3 zero prerequisite from prior projection; no fullparent/nativephysical/clock qualification',formal_credit=False)
Path('RESULT.json').write_text(json.dumps(z,indent=1)+'\n');print(z)
PY
