#!/bin/bash
# DIE-HBM-101: G0 check.py on hp3 (baseline) and hp4, same tool tree as B10X-1 g0.sh
S=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18; H=/srv/opentallas-scratch2/claude/die-proto-3/hbm/hp1lane
cd $S
for p in hp5a; do O=$H/g0_$p; mkdir -p $O
  nice -n 10 python3 -I tools/die_plan/check.py $H/plans/$p/die_plan.json --out $O/g0_report.json --quiet > $O/g0.log 2>&1 &
done
wait; for p in hp5a; do echo "$p done"; done
