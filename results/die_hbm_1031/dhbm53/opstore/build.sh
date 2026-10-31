#!/bin/bash
# DIE-HBM-53: opstore grow variants: opstore_grow.py -> core_macros_fix --static -> station_resite (q_b113, reach 360) -> G0 + G0C
W=/srv/opentallas-scratch2/claude/wt/die-hbm-49; cd /srv/opentallas-scratch2/claude/die-hbm-53/ops
for v in A B; do (
  rm -rf cm$v rs$v d$v
  python3 $W/physical/die_plan/hbm/core_macros_fix.py pre$v --out cm$v --lef-dir /srv/opentallas-scratch2/claude/die-hbm-53/q3/lefall --static pre$v/S_opstore.json > cm$v.log 2>&1 || { echo CMFAIL >> cm$v.log; exit 1; }
  python3 $W/tools/die_plan/station_resite.py cm$v rs$v --types q_b113,q_b113__physical_v1 --reach 360 --jobs 8 > rs$v.log 2>&1 || { echo RSFAIL >> rs$v.log; exit 1; }
  cp -al cm$v d$v; for f in die_plan.json station_resite_report.json; do rm -f d$v/$f; cp rs$v/$f d$v/$f; done; rm -rf rs$v
  mkdir -p g0$v
  python3 $W/tools/die_plan/check.py d$v/die_plan.json --out g0$v/g0.json > g0$v/g0.log 2>&1 &
  python3 $W/tools/die_plan/check.py d$v/die_plan.json --completeness --out g0$v/g0c.json > g0$v/g0c.log 2>&1 &
  wait ) &
done; wait; echo ALLDONE
