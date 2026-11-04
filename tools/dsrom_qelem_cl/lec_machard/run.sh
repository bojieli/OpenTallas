#!/bin/bash
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
cd /w
$Y -q -l gold.log -s gold.ys; echo gold rc=$?
$Y -q -l gate.log -s gate.ys; echo gate rc=$?
python3 -I - <<'P'
import re
s=open('gate.il').read()
s2=re.sub(r'g_mh\.g_m\[(\d)\]\.u_m\.',lambda m:'g_mac[%s].'%m.group(1),s)
open('gate2.il','w').write(s2)
print('renamed',s.count('g_mh.g_m['),s2.count('g_mh.g_m['))
P
$Y -q -l eq.log -s eq.ys; echo eq rc=$?
