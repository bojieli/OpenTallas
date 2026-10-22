#!/usr/bin/env bash
set -eu
O=$1
mkdir -p "$O"
iverilog -g2012 -s tb_s81_land -DTB_W=276 -DTB_D=32 -DTB_KW=6 -DTB_NMAX=8 -DTB_TOP=${PV_TOP:-dsdv_pv_local_land_n32_276} -o "$O/sim" tools/s81_dv/pv_local_d32_n32/tb.sv ${PV_RTL:-rtl/dsrom_sys/s81_dv/land/dsdv_pv_local_n32.sv} rtl/common/landed_parent/ot_pl_land_reset_forest.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv
for pair in 115:0 815:0 115:700; do
 d=${pair%:*}; r=${pair#*:}
 vvp -n "$O/sim" +N=0 +DH="$d" +LR="$r" +K=17 +R0=12 +G=12 +RL=2 +IR=2 +GS=4 +CYC=256 > "$O/p_${d}_${r}.log"
done
vvp -n "$O/sim" +N=0 +DH=115 +LR=0 +K=16 +R0=12 +G=12 +RL=2 +IR=2 +GS=4 +CYC=256 > "$O/invalid_k.log"
python3 - "$O" "${2:-suite}" <<'PY'
import sys,re,json
from pathlib import Path
p=Path(sys.argv[1]);rows=[]
for f in sorted(p.glob('*.log')):
 s=f.read_text();m=re.search('OT_LAND (.*)',s);assert m,s
 d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',m.group(1))}
 if f.name.startswith('p_'):assert d['mism']==0 and d['fault']==0 and d['meas']==18,d
 else:assert d['fault']==1 and d['mism']>0,d
 rows.append(dict(file=f.name,result=d))
(p/'receipt.json').write_text(json.dumps(dict(verdict='PASS',kit_reset=2,internal_reset=2,total_reset=4,K=17,cases=rows),indent=2)+'\n');print('PV_LOCAL_D32_N32_PASS',len(rows))
if sys.argv[2]=='invalid_k':
 print('PV_LOCAL_INVALID_K_CAUGHT');sys.exit(1)
PY
