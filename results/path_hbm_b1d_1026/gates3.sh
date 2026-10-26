#!/bin/bash
# D-HBM-B1 clock-entry delta gates. G0/G0C + G2 escape: plan tools codex/hbm-native-1026@2533b7f2c (+ main f1ea76b2d FIRM g2 fix);
# master plan: main ac2ad01a82 (native clock-pin check) and road codex/hbm-road-1026@41bf7f8d8 (master_exact tool lineage)
D=/srv/opentallas-scratch2/claude/path-hbm/b1d_1026; M=/srv/opentallas-scratch2/claude/wt/hbm-b1-delta-1026; N=/srv/opentallas-scratch2/claude/wt/hbm-b1-native-ro-1026; R=/srv/opentallas-scratch2/claude/wt/hbm-b1-road-ro-1026
cd $D/plan_b1d
( python3 $N/tools/die_plan/check.py die_plan.json --completeness --out gates/g0c > gates-g0c.log 2>&1; echo $? > gates-g0c.exit ) &
( python3 $M/tools/die_plan/die_infra.py master-plan die_plan.json --out $D/mp_main_b1d --entries entries.json > $D/mp_main_b1d.log 2>&1; echo $? > $D/mp_main_b1d.exit ) &
( python3 $R/tools/die_plan/die_infra.py master-plan die_plan.json --out $D/mp_road_b1d --entries entries.json > $D/mp_road_b1d.log 2>&1; echo $? > $D/mp_road_b1d.exit ) &
( python3 $N/tools/die_plan/g2.py part die_plan.json --out $D/g2_escape --types q_b100,q_b101,q_b101_nw --run --mem 32 > $D/g2_escape.log 2>&1; echo $? > $D/g2_escape.exit ) &
wait; echo done
