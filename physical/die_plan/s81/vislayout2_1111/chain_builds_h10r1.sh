#!/bin/bash
# chain_builds.sh : after the strict bind of plan_h2_h10r1 passes (BIND_RC=0, 0 errors), build both col_h10_r1 types in parallel
set -u; cd /
X=/srv/opentallas-scratch2/claude/vislayout2-s81/sub/h10r1; L=$X/b/bind_h10r1.log
until grep -q "^BIND errors" $L; do sleep 30; done
if grep -q "^BIND_RC=0" $L && grep -q "^BIND errors 0 " $L; then
  for t in col_h10_r1__t1__cl95b37463 col_h10_r1__t1__cld01bb4ae; do
    BIND=$X/b/bind_h10r1 setsid nohup bash $X/tools/build_type_pc.sh $t $X/b/bind_h10r1.plandir/plan_vl2.json h10r1 > $X/b/build_${t##*__}.log 2>&1 < /dev/null &
  done
  echo "CHAIN launched 2 builds $(date)"
else
  echo "CHAIN bind failed, no builds $(date)"
fi
