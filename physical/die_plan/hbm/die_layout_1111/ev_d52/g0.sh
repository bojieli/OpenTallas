#!/bin/bash
cd /srv/opentallas-scratch2/claude/kw45/src_hbm_main_fe0002fac6 || exit 9
E=/srv/opentallas-scratch2/claude/die-layout-hbm/bind/ev52
for p in pB; do python3 -I tools/die_plan/check.py $E/$p/die_plan.json --out $E/g0_$p > $E/g0_$p.log 2>&1 & done; wait
for p in pB; do python3 -I -c "import json,sys;r=json.load(open(sys.argv[1]));f=r['findings'];print(sys.argv[2],'ERR',sum(1 for x in f if x.get('level')=='ERROR'),'WARN',sum(1 for x in f if x.get('level')=='WARN'))" $E/g0_$p/g0_report.json $p; done
