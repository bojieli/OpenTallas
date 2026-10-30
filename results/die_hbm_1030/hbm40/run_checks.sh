#!/bin/bash
# G0 + G0C + strict all-gap bind on plan/$1 with wt/die-hbm-40 tools (= die-hbm-39 branch tools, same as d38s baseline)
R=/srv/opentallas-scratch2/claude/die-hbm-40; WT=/srv/opentallas-scratch2/claude/wt/die-hbm-40; P=$1
mkdir -p $R/g0/$P $R/bind/$P; cd $WT; ulimit -v 30000000
( python3 tools/die_plan/check.py $R/plan/$P/die_plan.json --out $R/g0/$P/g0_report.json > $R/g0/$P/g0.log 2>&1; echo $? > $R/g0/$P/g0.rc
  python3 tools/die_plan/check.py $R/plan/$P/die_plan.json --completeness --out $R/g0/$P/g0c_report.json > $R/g0/$P/g0c.log 2>&1; echo $? > $R/g0/$P/g0c.rc ) &
python3 -u tools/die_plan/bind.py bind $R/plan/$P/die_plan.json --asbuilt /srv/opentallas-scratch2/claude/die-hbm-39/bind/asbuilt.json --out $R/bind/$P/out --strict --all-gaps --mem 24 > $R/bind/$P/bind.log 2>&1; echo $? > $R/bind/$P/bind.rc
wait; touch $R/bind/$P/done
