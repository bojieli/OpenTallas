#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
P=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
cat "$P"/*SEQ*RVT_TT*.lib > /o/seq.lib
python3 - <<'LIB'
import gzip,glob,re
r='/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'
bodies=[]
for pat in ['*SIMPLE*RVT_TT*.lib.gz','*INVBUF*RVT_TT*.lib.gz']:
 for f in glob.glob(r+'/'+pat):
  s=gzip.open(f,'rt').read();bodies.append(s[s.index('{')+1:s.rfind('}')])
open('/o/simple.lib','w').write('library(joint) {\n'+'\n'.join(bodies)+'\n}\n')
LIB
for f in native bounded; do
 flag=""; if [ "$f" = bounded ]; then flag="-DBOUNDED"; fi
 yosys -Q -T -p "read_verilog -sv $flag /o/origin.sv /o/wrapper.sv; synth -top joint_stage -flatten; dfflibmap -liberty /o/seq.lib; abc -liberty /o/simple.lib; clean; write_verilog -noattr /o/$f.v; stat" > /o/$f.log 2>&1
done
