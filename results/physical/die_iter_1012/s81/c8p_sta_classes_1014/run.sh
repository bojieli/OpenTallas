#!/bin/bash
set -e
B=/srv/opentallas-scratch/claude/s81-die-iter
D=$B/c8p/class_1014
G=$B/c8p/grt
K=$B/c8p/kit/clock_delivery.json
mkdir -p $D; cd $D
cp $B/xsp0_screen/plan.json.gz plan.json.gz
cp $B/src_fc4ecfdca/tools/s81/sta_path_classes.py .
python3 - <<'PY'
import json,sys
from pathlib import Path
root=Path('/srv/opentallas-scratch/claude/s81-die-iter/src_fc4ecfdca')
sys.path.insert(0,str(root/'tools'))
import os; os.chdir(root)
import dsrom_s81_fulldie as G
G.Q_LEF='physical/s81_die_views/q_elem_qs5f_efs/q_elem.lef.gz'
mapping={}
for master,ports in G.real_ports_r8().items():
 a={}
 for port,pins in ports.items():
  for bit,pin in enumerate(pins):
   a[pin]=[port,bit]
 mapping[master]=a
Path('/srv/opentallas-scratch/claude/s81-die-iter/c8p/class_1014/real_pin_aliases.json').write_text(json.dumps(mapping)+'\n')
print('aliases',len(mapping),sum(map(len,mapping.values())))
PY
python3 - <<'PY' > census.json
import gzip,json,re
p=json.load(gzip.open('plan.json.gz'))
pm={i[0]:i[1] for i in p['insts']}
dm={}
for ln in open('/srv/opentallas-scratch/claude/s81-die-iter/c8p/a_real/die.v'):
    m=re.match(r'\s*(\S+)\s+(\S+)\s*\(',ln)
    if m and m[1] not in ('module','input','output','wire','assign'): dm[m[2]]=m[1]
miss=[k for k in pm if k not in dm]; extra=[k for k in dm if k not in pm]
mm=[k for k in pm if k in dm and dm[k]!=pm[k]]
print(json.dumps(dict(plan=len(pm),die_v=len(dm),missing=len(miss),extra=len(extra),master_mismatch=len(mm),ex_missing=miss[:5],ex_extra=extra[:5],ex_mm=mm[:5])))
PY
cat census.json
for c in tt ss ff; do python3 sta_path_classes.py plan.json.gz $G/end_$c.rpt $K classes_$c.json --pin-aliases real_pin_aliases.json > classes_$c.log 2>&1 & done
wait
sha256sum $G/end_*.rpt $K $B/c8p/a_real/die.v sta_path_classes.py plan.json.gz > sha256.txt
echo DONE
