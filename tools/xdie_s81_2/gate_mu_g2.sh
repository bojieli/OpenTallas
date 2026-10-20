#!/bin/bash
# S81-TOK4 (10-19): fluid guard 2 / window 3 rerun on the EXISTING builds (out_a/bA MU 2, out_c/bC MU 0, out_x/bL LAND_MUT_SEL).
# Guard 1 left 1 instance late by +1 in a23r (cand_merge u34, 708 beats) and 11 in a46d (3164 beats): the fluid queue
# bounds the slot phase only to [-1, +2] under dense MU traffic. Goldens: goldens_g2/<g> = gen_golden.py --dl-model fluid --fluid-guard 2.
#   bash tools/xdie_s81_2/gate_mu_g2.sh out_g2
set -u; O=$1; mkdir -p $O
X="bash tools/xdie_s81_2/xdie2.sh"; GD=goldens_g2
r() { n=$1; b=$2; g=$3; shift 3
      ( $X run $O $b $n $GD/$g "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt
        python3 tools/xdie_s81_2/mu_check.py $GD/$g $O/$n/run.log --win 3 --json $O/$n.chk.json > $O/$n.chk.txt 2>&1
        echo "EXIT $?" >> $O/$n.chk.txt; gzip -kf $O/$n/run.log; rm -f $O/$n/run.log $O/$n/stim.hex ) & }
for b in bA bC bL; do src=out_a; [ $b = bC ] && src=out_c; [ $b = bL ] && src=out_x; ln -sfn ../$src/$b $O/$b; done
r a_su bA su; r a_a23r bA a23r; r a_a46d bA a46d; r a_a46d_err bA a46d +ERRP=7
r c_g1 bC g1; r c_g1_err bC g1 +ERRP=7; r x_landsel bL su
wait; touch $O/DONE_g2
