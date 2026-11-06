#!/bin/bash
set -euo pipefail
out=/srv/opentallas-scratch2/claude/codex-hbm-tkm-cts-query
cd "$out"
grep -q 'SUCCESS' shadow_eq.log
grep -q 'proof did fail' shadow_mutant.log
iverilog -g2012 -s tb -o shadow.vvp tkshadow_formal.sv tkshadow_tb.sv
vvp shadow.vvp > shadow_lockstep.log
iverilog -g2012 -D MUTANT -s tb -o shadow_mut.vvp tkshadow_formal.sv tkshadow_tb.sv
vvp shadow_mut.vvp > shadow_mutant_lockstep.log
iverilog -g2012 -E -o base_off.pp base_source.sv
iverilog -g2012 -E -o shadow_off.pp shadow_source.sv
iverilog -g2012 -E -DOT_TKM_DEL_PIPE1 -DOT_TKM_PAR_MERGE -o base_pmerge.pp base_source.sv
iverilog -g2012 -E -DOT_TKM_DEL_PIPE1 -DOT_TKM_PAR_MERGE -o shadow_pmerge.pp shadow_source.sv
python3 - <<'PY'
import re,json
from pathlib import Path
z={}
for mode in ['off','pmerge']:
 a=Path(f'base_{mode}.pp').read_text();b=Path(f'shadow_{mode}.pp').read_text()
 a=re.sub(r'`line[^\n]*','',a);b=re.sub(r'`line[^\n]*','',b)
 assert ''.join(a.split())==''.join(b.split()),mode
 z[mode]='TOKEN_IDENTICAL'
Path('shadow_default_identity.json').write_text(json.dumps(z,indent=2))
PY
docker run --rm --name tkshadow-finish-$BASHPID --cpus=1 --memory=4g --memory-swap=4g -v "$out:/work" -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
yosys -Q -p "read_verilog -sv -DOT_TKM_DEL_PIPE1 -DOT_TKM_PAR_MERGE -DOT_TKM_TK_SHADOW shadow_source.sv; hierarchy -top ot_hgi_coll_tkm_tp192_root_core_x; proc; opt_clean; write_json shadow_full.json" > shadow_full.log 2>&1
python3 /work/extract_shadow.py
python3 /work/map_shadow.py
'
