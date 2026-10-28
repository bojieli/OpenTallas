#!/bin/bash
# DIE-HBM-5: bind all + kit-rtl per partition type on C20i-po (COORD 04:1x prerequisite for HBM region kits)
cd /srv/opentallas-scratch2/claude/die-hbm-5
T=/srv/opentallas-scratch2/claude/wt/die-hbm-5/tools/die_plan
echo START $(date) > bind_c20i.log
python3 $T/bind.py all c20i_po/die_plan.json --out bind_c20i --mem 64 >> bind_c20i.log 2>&1; rc=$?
echo BIND_RC $rc $(date) >> bind_c20i.log
[ $rc = 0 ] || exit $rc
for t in $(python3 -c "import json;print(\" \".join(json.load(open(\"c20i_po/die_plan.json\"))[\"partition_types\"]))"); do
  python3 $T/bind.py kit-rtl c20i_po/die_plan.json --out bind_c20i --type $t >> bind_c20i_kitrtl.log 2>&1 && echo OK $t >> bind_c20i.log || echo FAIL $t >> bind_c20i.log
done
echo END $(date) >> bind_c20i.log
