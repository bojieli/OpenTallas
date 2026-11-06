#!/bin/bash
set -u; Q=/srv/opentallas-scratch2/claude/hbm-reform-b5/q2n; R=/srv/opentallas-scratch3/claude/hbm-reform-b3/wt; H=physical/die_plan/hbm/cores/harden
git -C $R show 97b0810d61:$H/rest_wrap.py > $Q/rest_wrap.py
python3 -I - <<'P'
import json
u={"vm_rr":[256,513,770,1027,1284,1541,1798,2055],"clk_reduce":[0],"clk_qslots":list(range(10))}
json.dump(u,open('/srv/opentallas-scratch2/claude/hbm-reform-b5/q2n/use_rest.json','w'))
P
python3 -I $Q/rest_wrap.py --ext $Q/rest/ot_q2nf_rest_x.v --name ot_q2nf_rest_x --top ot_q2nf_rest --use $Q/use_rest.json --parent $Q/rest/ot_q2nf_rest_x.parent.v --out $Q/gen/ot_q2nf_rest.sv --hdr "// GENERATED (HBM-REFORM-B5) by rest_extract.sh + rest_wrap.py from the q2n2 body master with the qslots tile cut, see gen_q2n.py." 2>&1 | tail -3 | cut -c1-220
L=$(grep -n '^module ot_q2nf_rest (' $Q/gen/ot_q2nf_rest.sv | cut -d: -f1); sed -n "$L,\$p" $Q/gen/ot_q2nf_rest.sv | sed -n '/^);/q;p' | cut -c1-90 | grep -iv "clk\|cfg_\|desc_" | head -60
