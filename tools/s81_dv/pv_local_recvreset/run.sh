#!/usr/bin/env bash
set -eu
out=$1
mkdir -p "$out"
iverilog -g2012 -s tb_s81_land -DTB_W=276 -DTB_D=32 -DTB_KW=6 -DTB_NMAX=8 -DTB_TOP=dsdv_pv_local_land_recvreset_276 -o "$out/sim" tools/s81_dv/pv_local_recvreset/tb.sv rtl/dsrom_sys/s81_dv/land/dsdv_pv_local_recvreset.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv
for pair in 115:0 815:0 115:700; do
 d=${pair%:*}; r=${pair#*:}
 vvp -n "$out/sim" +N=0 +DH="$d" +LR="$r" +K=17 +R0=12 +G=12 +RL=2 +IR=4 +GS=4 +CYC=256 > "$out/p_${d}_${r}.log"
done
python3 - "$out" <<'PY'
from pathlib import Path
import re,sys,json
p=Path(sys.argv[1]);rows=[]
for f in sorted(p.glob('p_*.log')):
 s=f.read_text();m=re.search(r'OT_LAND (.*)',s);assert m,s
 d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',m.group(1))};rows.append(dict(file=f.name,measurement=d))
# Initial measurement only: preserve the original book and classify any
# mismatch. A source-clock preamble is not silently represented as ck edges.
r=dict(scope='unselected receiving-reset mechanism; explicit preamble and independent reader reset; no production date qualification',writer_preamble_ck_f_edges=2,reader_reset_ck_edges=4,kit_reset_ck_edges=2,cases=rows)
for row in rows:
 d=row['measurement']; assert d['mism']==0 and d['fault']==0 and d['meas']==18, row
(p/'measurement.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
