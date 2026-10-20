#!/bin/bash
# TOKSIM-S81C/XUG2 (10-19): job u (MU 1, bU) on the fluid guard-2 deadline model, mu_check --win 3 (S81-TOK4 fix: guard 1
# lands dense MU beats at deadline+1). cwd = staged root (stage.sh, DIE = mu3 ceaed19c4). Schedule-only change: same bU
# build as gate_mu.sh u (MU 1, $BIG), goldens + check differ.
# Step 1 generates the missing guard-2 goldens (ar46r ar46d mtp10r mtp10d) with the ORIGINAL mu args. The args are first
# proven: the same args at guard 1 must reproduce goldens/<g> byte-identically (stim.hex, mu.hex, NS, NM, golden.json),
# else GEN_ARGS_MISMATCH and no run starts. The bU build runs in parallel with the goldens.
#   bash tools/xdie_s81_2/gate_mu_u_g2.sh out_u5
set -u; O=$1; mkdir -p $O
X="bash tools/xdie_s81_2/xdie2.sh"; GD=goldens_g2; GEN="python3 tools/xdie_s81_2/gen_golden.py --gap 100 --dl-model fluid"
BIG="-GNSMAX=327680 -GQD=32768 -GMAXCYC=1600000 -GNMMAX=2048"
( $X build $O bU mu -GMU=1 $BIG > $O/build_bU.txt 2>&1; echo "EXIT $?" >> $O/build_bU.txt ) &
BPID=$!
declare -A ARGS=(
  [ar46r]="--mu-users 46 --mu-mode real --mu-cal cal_ar_q4.json"
  [ar46d]="--mu-users 46 --mu-mode dense"
  [mtp10r]="--mu-users 10 --mu-mode real --mu-cal cal_mtp_q4.json"
  [mtp10d]="--mu-users 10 --mu-mode dense" )
mkdir -p $O/gen_g1chk $O/gen_g2
gen() { g=$1
  $GEN ${ARGS[$g]} --fluid-guard 1 --out $O/gen_g1chk/$g > $O/gen_g1chk/$g.log 2>&1 || { echo "GEN_FAIL g1 $g"; return 1; }
  for f in stim.hex mu.hex NS NM golden.json; do
    cmp -s $O/gen_g1chk/$g/$f goldens/$g/$f || { echo "GEN_ARGS_MISMATCH $g $f"; return 1; }; done
  echo "GEN_ARGS_OK $g (guard 1 reproduces goldens/$g byte-identically)"
  $GEN ${ARGS[$g]} --fluid-guard 2 --out $O/gen_g2/$g > $O/gen_g2/$g.log 2>&1 || { echo "GEN_FAIL g2 $g"; return 1; }
  echo "GEN_G2_OK $g $(cat $O/gen_g2/$g.log)"; }
ok=1; pids=()
for g in ar46r ar46d mtp10r mtp10d; do ( gen $g > $O/gen_$g.status 2>&1 ) & pids+=($!); done
for p in "${pids[@]}"; do wait $p || ok=0; done
cat $O/gen_*.status
if [ $ok = 1 ]; then
  for g in ar46r ar46d mtp10r mtp10d; do
    if [ -e $GD/$g ]; then cmp -s $GD/$g/stim.hex $O/gen_g2/$g/stim.hex && cmp -s $GD/$g/golden.json $O/gen_g2/$g/golden.json \
      || { echo "G2_EXISTS_DIFFERENT $g"; ok=0; }
    else mv $O/gen_g2/$g $GD/$g; cp $O/gen_g2/$g.log gen_g2_$g.log; fi
  done
  rm -rf $O/gen_g1chk/*/stim.hex
fi
wait $BPID
grep -q "^BUILD_OK bU" "$O/build_bU.txt" || { touch "$O/DONE_u_g2_FAILED"; exit 3; }
tail -2 $O/build_bU.txt
[ $ok = 1 ] || { echo "NO_RUNS (golden step failed)"; touch $O/DONE_u_g2_FAILED; exit 2; }
CHECK_WIN=3
source tools/xdie_s81_2/gate_result.sh
SU_GUARD=2; prepare_mu_su || exit $?
r u_su bU "$O/su_mu"; r u_ar46r bU ar46r; r u_ar46d bU ar46d; r u_ar46d_err bU ar46d +ERRP=7; r u_mtp10r bU mtp10r; r u_mtp10d bU mtp10d
finish_jobs u_g2 || exit $?
for n in u_su u_ar46r u_ar46d u_ar46d_err u_mtp10r u_mtp10d; do echo "== $n"; tail -3 $O/$n.txt; tail -4 $O/$n.chk.txt; done
