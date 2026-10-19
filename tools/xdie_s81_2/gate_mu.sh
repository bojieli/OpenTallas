#!/bin/bash
# XDIE-S81-MU gate (10-19), cwd = staged root (stage.sh, DIE = mu3 ceaed19c4 = the MU release die RTL of the mu4 bind).
# Goldens pre-generated under goldens/ with gen_golden.py --dl-model fluid (phase-free compiler crossing deadlines):
#   su      single user (MU vehicle, user 0, real start)          ar46r / ar46d  46 AR users, real shifts / dense 150
#   mtp10r / mtp10d  10 MTP users (calendar_mtp_q4 shifts / dense)
#   a23r    the 23 copy-A users of the AR calendar at their real shifts, all ab 0 (MU die, copy-A-only endpoints)
#   a46d    46 users dense, all ab 0 (MU die)                      g1   single-user TP calendar (MU 0, reps 2)
# Jobs: u = MU 1 (copy-A/B superset, lep_mu_ab everywhere, 4 lane tiles/endpoint)   a = MU 2 (MU die leaves exactly)
#       c = MU 0 (single-user die path)   x = mutants on MU 2 (STALEHD: show-ahead head bug -> bench FAIL;
#       LAND_MUT_SEL: landing slot one cycle early -> mu_check WIN_FAIL)
# Every run is followed by tools/xdie_s81_2/mu_check.py (two-sided window [deadline - 2, deadline] + per-user invariance).
# bash tools/xdie_s81_2/gate_mu.sh <out> u|a|c|x
set -u; O=$1; JOB=$2; mkdir -p $O
X="bash tools/xdie_s81_2/xdie2.sh"; GD=goldens
BIG="-GNSMAX=327680 -GQD=32768 -GMAXCYC=1600000 -GNMMAX=2048"
r() { n=$1; b=$2; g=$3; shift 3
      ( $X run $O $b $n $GD/$g "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt
        python3 tools/xdie_s81_2/mu_check.py $GD/$g $O/$n/run.log --json $O/$n.chk.json > $O/$n.chk.txt 2>&1
        echo "EXIT $?" >> $O/$n.chk.txt; gzip -kf $O/$n/run.log ) & }
bld() { b=$1; shift; $X build $O "$@" > $O/build_$b.txt 2>&1; echo "EXIT $?" >> $O/build_$b.txt; }
case $JOB in
  u) bld bU bU mu -GMU=1 $BIG
     r u_su bU su; r u_ar46r bU ar46r; r u_ar46d bU ar46d; r u_ar46d_err bU ar46d +ERRP=7; r u_mtp10r bU mtp10r; r u_mtp10d bU mtp10d ;;
  a) bld bA bA mu -GMU=2 $BIG
     r a_su bA su; r a_a23r bA a23r; r a_a46d bA a46d; r a_a46d_err bA a46d +ERRP=7 ;;
  c) bld bC bC cur $BIG
     r c_g1 bC g1; r c_g1_err bC g1 +ERRP=7 ;;
  x) bld bS bS mu -GMU=2 $BIG +define+OT_S81SL_LEP_MUT_STALEHD; r x_stalehd bS su
     bld bL bL mu -GMU=2 $BIG +define+OT_S81_LAND_MUT_SEL; r x_landsel bL su ;;
esac
wait; touch $O/DONE_$JOB
