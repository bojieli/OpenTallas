#!/bin/bash
set -e
D=/srv/opentallas-scratch/claude/s81-die-iter/c7p/class_1014
G=/srv/opentallas-scratch/claude/s81-die-iter/c7p/grt
K=/srv/opentallas-scratch/claude/s81-die-iter/c7p/kit/clock_delivery.json
cd $D
python3 - <<'PY' > census.json
import gzip,json,re
p=json.load(gzip.open('plan.json.gz'))
pm={i[0]:i[1] for i in p['insts']}
dm={}
for ln in open('/srv/opentallas-scratch/claude/s81-die-iter/c7p/a_real/die.v'):
    m=re.match(r'\s*(\S+)\s+(\S+)\s*\(',ln)
    if m and m[1] not in ('module','input','output','wire','assign'): dm[m[2]]=m[1]
miss=[k for k in pm if k not in dm]; extra=[k for k in dm if k not in pm]
mm=[k for k in pm if k in dm and dm[k]!=pm[k]]
print(json.dumps(dict(plan=len(pm),die_v=len(dm),missing=len(miss),extra=len(extra),master_mismatch=len(mm),ex_missing=miss[:5],ex_extra=extra[:5],ex_mm=mm[:5])))
PY
for c in tt ss ff; do python3 sta_path_classes.py plan.json.gz $G/end_$c.rpt $K classes_$c.json --pin-aliases real_pin_aliases.json > classes_$c.log 2>&1 & done
wait
sha256sum $G/end_*.rpt $K /srv/opentallas-scratch/claude/s81-die-iter/c7p/a_real/die.v sta_path_classes.py plan.json.gz > sha256.txt
echo DONE
