#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'INNER'
from pathlib import Path
libs=['/work/'+x+'.lib' for x in ['AO','INVBUF','OA','SEQ','SIMPLE']]
rows=['read_liberty -lib '+f for f in libs]
rows+=['read_verilog -sv /work/ve_native32_limit32.v','hierarchy -check -top ot_s81sl_ve_native32','tcl /work/ot_keep_regs.tcl','synth -top ot_s81sl_ve_native32 -flatten','dfflibmap -liberty /work/SEQ.lib','abc '+' '.join('-liberty '+f for f in libs)+' -D 770','clean','stat','write_verilog -noattr /work/ve_retained.v','write_json /work/ve_retained.json']
Path('retain.ys').write_text('\n'.join(rows)+'\n')
INNER
docker run --rm --memory=64g --memory-swap=64g -v "$PWD:/work" -w /work openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -l retain_yosys.log -s retain.ys; python3 mapped_census.py --tool tools/textbook_lint.py --netlist ve_retained.v --top ot_s81sl_ve_native32 --out ve_retained_census.json' > retain.log 2>&1
echo VE_RETAIN_DONE
