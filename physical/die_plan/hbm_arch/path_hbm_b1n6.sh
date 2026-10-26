#!/bin/bash
# b1n6 = b1n5 -> q_b101 + q_b101_nw idx column re-lattice (C01/C12 14.688 -> 23.328 um, 0 cycles) -> census complete (L12x1)
set -u
WT=/srv/opentallas-scratch2/claude/wt/claude-hbm-b1-native-1026
D=/srv/opentallas-scratch2/claude/path-hbm/g0cfix_1026; B=/srv/opentallas-scratch2/claude/path-hbm/b1c_1026
export PYTHONPATH=$D/pyx; cd $WT
H=physical/die_plan/hbm_arch
rm -rf $D/b1n6_s1 $D/b1n6_s2 $D/plan_b1n6
for T in q_b101 q_b101_nw; do
  [ $T = q_b101 ] && SRC=$D/plan_b1n5 OUT=$D/b1n6_s1 || SRC=$D/b1n6_s1 OUT=$D/b1n6_s2
  python3 $H/path_hbm_b100_escape.py --src $SRC --out $OUT --type $T --cols 8.64,250.56,492.48 --slot none --recentre L12x1 > $D/b1n6_$T.log 2>&1 || { echo ESC_FAIL $T; tail -3 $D/b1n6_$T.log; exit 3; }
done
python3 $H/path_hbm_census_complete.py --src $D/b1n6_s2 --out $D/plan_b1n6 --types q_b101,q_b101_nw > $D/b1n6_s3.log 2>&1; echo "census tool exit $?"
[ -f $D/plan_b1n6/die_plan.json ] || { echo S3_FAIL; exit 5; }
rm -rf $D/b1n6_s1 $D/b1n6_s2
cd $D/plan_b1n6; rm -rf gates gates-g0*.log gates-g0*.exit b1_verify.json cut_all.json
sha256sum die_plan.json > die_plan.sha256
python3 $B/cut_all.py $WT/tools/die_plan $PWD/cut_all.json $PWD/die_plan.json > cut_all.log 2>&1 &
python3 $B/b1_verify.py $WT/tools/die_plan $PWD $PWD/b1_verify.json > b1_verify.log 2>&1 &
(python3 $WT/tools/die_plan/check.py die_plan.json --out gates/g0 --png > gates-g0.log 2>&1; echo $? > gates-g0.exit) &
python3 $WT/tools/die_plan/check.py die_plan.json --completeness --out gates/g0c > gates-g0c.log 2>&1; echo $? > gates-g0c.exit
wait; echo done
