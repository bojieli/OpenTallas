#!/bin/bash
set -eu
TASK=/var/tmp/ctlm-split-1013
RS="$TASK/src-ce3-power-local"
mkdir -p "$RS"
tar -xf "$TASK/ce3.tar" -C "$RS"
cd "$RS"
python3 - <<'PY'
p='physical/qfd_tt_ctlm_split/bench.sh'
s=open(p).read().replace('if(me_clk_en_1) p_edges1','if(u1.u_tree.local_en) p_edges1').replace('if(me_clk_en_1) p_idleclk1','if(u1.u_tree.local_en) p_idleclk1')
open(p,'w').write(s)
PY
bash physical/qfd_tt_ctlm_split/bench.sh "$TASK/out/ce3-power-local" power
