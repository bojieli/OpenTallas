#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
sed 's/ot_hgi_coll_reduce_static #/ot_hgi_coll_reduce_static_pr #/g;s/#(.LOCAL_CTRL(1))/#()/g' tb.sv > tb_pr.sv
iverilog -g2012 -DOT_HBM_REDUCE_LOCAL_CTRL -s tb -o pr_good tb_pr.sv arith_contract.sv ot_hgi_coll_reduce_static.sv ot_hgi_coll_reduce_static_pr.sv
vvp pr_good > pr_good.log
python3 - <<'PY2'
from pathlib import Path
s=Path('ot_hgi_coll_reduce_static.sv').read_text();assert s.count('tag_q<=pipe_tag[6]')==1
Path('mut.sv').write_text(s.replace('tag_q<=pipe_tag[6]','tag_q<=pipe_tag[5]'))
PY2
iverilog -g2012 -DOT_HBM_REDUCE_LOCAL_CTRL -s tb -o pr_bad tb_pr.sv arith_contract.sv mut.sv ot_hgi_coll_reduce_static_pr.sv
set +e
vvp pr_bad > pr_bad.log
rc=$?
set -e
if [ "$rc" = 0 ]; then echo PR_MUTANT_NOT_CAUGHT;exit 2;fi
cat pr_good.log
head -n 5 pr_bad.log
echo PR_MUTANT_CAUGHT
