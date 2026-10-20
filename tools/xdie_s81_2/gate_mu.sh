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
source tools/xdie_s81_2/gate_result.sh
bld() { b=$1; shift; $X build "$O" "$@" > "$O/build_$b.txt" 2>&1; rc=$?; echo "EXIT $rc" >> "$O/build_$b.txt"; return "$rc"; }
[ "$JOB" = c ] || prepare_mu_su || exit $?
case $JOB in
  u) bld bU bU mu -GMU=1 $BIG || exit $?
     r u_su bU "$O/su_mu"; r u_ar46r bU ar46r; r u_ar46d bU ar46d; r u_ar46d_err bU ar46d +ERRP=7; r u_mtp10r bU mtp10r; r u_mtp10d bU mtp10d ;;
  a) bld bA bA mu -GMU=2 $BIG || exit $?
     r a_su bA "$O/su_mu"; r a_a23r bA a23r; r a_a46d bA a46d; r a_a46d_err bA a46d +ERRP=7 ;;
  c) bld bC bC cur $BIG || exit $?
     r c_g1 bC g1; r c_g1_err bC g1 +ERRP=7 ;;
  x) # Require a source-pinned MU2 nominal control, using the exact mutant stimulus.
     NOM=${XDIE_NOMINAL_BUILD:-out_a/bA}
     [ -x "$NOM/obj/Vtb_xdie_s81_2" ] && [ -s "$NOM/sources.sha256" ] || { echo REFUSED_NO_PINNED_NOMINAL; exit 3; }
     grep -q -- '-GMU=2' "$NOM/build_cmd.txt" || { echo REFUSED_NOMINAL_MU_MODE; exit 3; }
     ln -s "$(realpath "$NOM")" "$O/bNom" || exit 3
     r x_nominal bNom "$O/su_mu"; finish_jobs x_nominal || exit $?; pids=()
     bld bS bS mu -GMU=2 $BIG +define+OT_S81SL_LEP_MUT_STALEHD || exit $?
     require_same_sources bNom bS || exit 3
     r_reject "^BENCH_FAIL" x_stalehd bS "$O/su_mu"
     bld bL bL mu -GMU=2 $BIG +define+OT_S81_LAND_MUT_SEL || exit $?
     require_same_sources bNom bL || exit 3
     r_reject "^WIN_FAIL" x_landsel bL "$O/su_mu" ;;
esac
finish_jobs "$JOB"
