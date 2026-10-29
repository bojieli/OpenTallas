#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
iverilog -g2012 -s tb -o good tb.sv arith_contract.sv ot_hgi_coll_reduce_static.sv
vvp good > good.log
python3 - <<'PY'
from pathlib import Path
p=Path('ot_hgi_coll_reduce_static.sv');s=p.read_text();assert s.count('tag_q<=pipe_tag[6]')==1
Path('mut.sv').write_text(s.replace('tag_q<=pipe_tag[6]','tag_q<=pipe_tag[5]'))
PY
iverilog -g2012 -s tb -o bad tb.sv arith_contract.sv mut.sv
set +e
vvp bad > bad.log
rc=$?
set -e
if [ "$rc" -eq 0 ]; then echo 'MUTANT NOT CAUGHT'; exit 2; fi
cat good.log
head -n 5 bad.log
echo MUTANT_CAUGHT
