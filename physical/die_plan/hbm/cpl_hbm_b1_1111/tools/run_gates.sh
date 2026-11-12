#!/bin/bash
# CPL-HBM-B1 gates on a candidate plan dir: G0 (worktree check.py 99d74f7714), stscan (bind vK5d_c12), route_supply. usage: run_gates.sh DIR
set -u; D=$(realpath $1); B=/srv/opentallas-scratch3/claude/cpl-hbm-b1/lad
( cd $B/wt && nice -n 19 python3 -I tools/die_plan/check.py $D/die_plan.json --out $D.g0/g0_report.json --quiet > $D.g0.log 2>&1; echo "rc $?" >> $D.g0.log ) &
( nice -n 19 python3 -I $B/bin/stscan.py $D $B/rtl --types q_b001,q_b001__physical_v1,q_b010,q_b010__physical_v1,q_b011,q_b011__physical_v1,q_b002,q_b003,q_b012,q_b013 --out $D.stscan.tsv --detail $D.stscan.json > $D.stscan.log 2>&1 ) &
( mkdir -p $D.rs && cd $B/wt && nice -n 19 python3 -I tools/die_plan/route_supply.py $D/die_plan.json --die hbm --repo . --ref-dirs $D --out $D.rs > $D.rs/rs.stdout 2> $D.rs/rs.stderr; echo "rc $?" >> $D.rs/rs.stdout ) &
wait; echo GATES_DONE
