#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir out3
sha256sum *.sv > out3/source.sha256
iverilog -g2012 -DTB_W=276 -DTB_D=32 -DTB_KW=6 -DTB_NMAX=128 -DTB_TOP=dsdv_pv_local_land_276 -o out3/d32 tb_s81_land.sv ot_s81_land.sv dsdv_pv_local_land.sv
iverilog -g2012 -DTB_W=276 -DTB_D=8 -DTB_KW=6 -DTB_NMAX=128 -o out3/d8 tb_s81_land.sv ot_s81_land.sv
for pair in 115:0 815:0 115:700; do
 delay=${pair%:*}; region=${pair#*:}
 vvp -n out3/d32 +N=0 +DH="$delay" +LR="$region" +K=17 +R0=12 +G=12 +CYC=256 > "out3/d32_${delay}_${region}.log"
 vvp -n out3/d8 +N=0 +DH="$delay" +LR="$region" +K=17 +R0=12 +G=12 +CYC=256 > "out3/d8_${delay}_${region}.log"
done
python3 - <<'PY'
import re,json,pathlib
rows=[]
for p in sorted(pathlib.Path('out3').glob('*.log')):
 s=p.read_text();m=re.search(r'OT_LAND (.*)',s);assert m,s
 d={k:int(v) for k,v in (t.split('=') for t in m.group(1).split())}
 if p.name.startswith('d32'):assert d['mism']==0 and d['fault']==0,d
 else:assert d['mism']>0 and d['meas']!=18,d
 rows.append(dict(file=str(p),result=d))
pathlib.Path('out3/receipt.json').write_text(json.dumps(dict(verdict='PASS',actual_d32_positive_and_d8_overwrite_causal=rows),indent=2)+'\n')
print('LOCAL_RING_D32_PASS_D8_CAUSAL',len(rows))
PY
