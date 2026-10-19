#!/bin/bash
# XDIE-S81-2 gate, cwd = staged root, goldens pre-generated under goldens/ (gen_golden.py; see README):
#   g556 = gate_g5's calendar (stim sha 3d0663...: LAT 556 = gate_g5, no lane legs)   g564 = same beats, LAT 556 + 8
#   (land_plan p4m: added_edges 4 a lane leg, one leg each end of a crossing)   gm564 = the reduced calendar (mutants)
#   mr / md = MU 3 users (real MU-S81 calendar shifts / dense 150-cycle gap)   mm = MU reduced (2 users, argmax + h)
# bash tools/xdie_s81_2/gate.sh <out> c|a|m|w
set -u; O=$1; JOB=$2; mkdir -p $O
X="bash tools/xdie_s81_2/xdie2.sh"; GD=goldens
r() { n=$1; b=$2; g=$3; shift 3; ( $X run $O $b $n $GD/$g "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt ) & }
bld() { b=$1; shift; $X build $O "$@" > $O/build_$b.txt 2>&1; echo "EXIT $?" >> $O/build_$b.txt; }
case $JOB in
  c) bld bC bC cur
     r min bC g564; r min_err bC g564 +ERRP=7; r chb0 bC g564 +CHB=0; r late bC gm564 +LATE=40 ;;
  a) bld bA bA asb; r asbound bA g564
     bld bN bN cur -GLEG=0; r noleg bN g556
     bld bL bL cur +define+OT_S81_LAND_MUT_SEL; r landsel bL gm564 ;;
  m) bld bM bM mu -GMU=1
     r mu_real bM mr; r mu_dense bM md; r mu_dense_err bM md +ERRP=7 ;;
  m2) # 10-19 re-run of the m runs on job m's build bM (same binary) with the MU goldens regenerated with the lep tag field
      # [1077:1045] zero on untagged TP beats (gen_golden MU_SPARE; the first m goldens put random payload there -> FINDING)
      ln -sfn ../out_m/bM $O/bM
      r mu_real bM mr; r mu_dense bM md; r mu_dense_err bM md +ERRP=7 ;;
  w) bld bMW bMW mu -GMU=1 +define+OT_S81SL_LEP_MUT_WRONGCOPY; r wrongcopy bMW mm
     bld bMT bMT mu -GMU=1 +define+OT_S81SL_LEP_MUT_TAGDROP; r tagdrop bMT mm ;;
esac
wait; touch $O/DONE_$JOB
