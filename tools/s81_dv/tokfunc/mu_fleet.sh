#!/bin/bash
# TOK-FUNC-S81/MURATE (10-21): fleet side of run_mu_calendar.sh (cwd = the staged root on the host; Verilator 5.050).
#   mu_fleet.sh build            build bG7 (xdie XL5 bench, MU 2 = the MU release die endpoints, WN = ot_s81sl_lep_mu_ab
#                                #(RX_SRAM 1, IN_PIPE 1, NATIVE32 1) as G7 binds s_0N; direct cabling D_CH 243 (TP leg 251)
#                                / D_ST 258 (stage-hop leg 266, hop_latency.json @4b528ad2b)), then the calibration runs
#                                cal_su / cal_mu1 (no deadlines) -> out/cal.json: measured fixed crossing per class
#                                (S / N = TP, H = stage hop); deadlines LAT = crossing + 1 (the r_dc_x recalibration rule)
#   mu_fleet.sh run <case>       generate the case golden (gen_golden.py, deadlines from cal.json) + run + lfix + per-user stats
# Cases: su | ar50r | mtp10r | ar50r_c<k> (users 5k..5k+5, real shifts rebased) | mtp10r_u<k> | ar50d | mtp10d |
#        hop_<plan name> (plans/<name>.json, mu_hop_plan.py)
set -u
O=out; mkdir -p $O goldens
X="bash tools/xdie_s81_2/xdie2.sh"
GEN="python3 tools/xdie_s81_2/gen_golden.py --xl5 --per S=1.345,N=1.345,H=1.345 --gap 100 --reserve-mu-tag"
CAL=cal
BIG="-GNSMAX=327680 -GQD=65536 -GMAXCYC=1800000 -GNMMAX=2048"
PAR="-GMU=2 -GXL5=1 -GD_CH=243 -GD_ST=258 -GLRXS=1 -GLINP=1 -GLN32=1"
lat() { python3 -c "import json; c=json.load(open('$O/cal.json')); print('S=%d,N=%d,H=%d' % (c['LAT']['S'], c['LAT']['N'], c['LAT']['H']))"; }
runcase() {  # runcase <name> <golden dir>
  n=$1; g=$2
  $X run $O bG7 $n $g > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt
  [ -f $O/$n/run.log ] && python3 tools/s81_dv/tokfunc/mu_stats.py $g $O/$n/run.log --cal $O/cal.json --out $O/$n/stats.json >> $O/$n.txt 2>&1
  [ -f $O/$n/run.log ] && gzip -f $O/$n/run.log
  rm -f $O/$n/stim.hex
  touch $O/DONE_$n
}
case $1 in
build)
  J=8 $X build $O bG7 g7 $PAR $BIG > $O/build_bG7.txt 2>&1; echo "EXIT $?" >> $O/build_bG7.txt
  grep -q "^BUILD_OK bG7" $O/build_bG7.txt || { touch $O/DONE_build_FAILED; exit 3; }
  $GEN --out goldens/cal_su > goldens/cal_su.log 2>&1 || exit 3
  $GEN --out goldens/cal_mu1 --mu-users 50 --mu-mode real --mu-cal $CAL/calendar_rel241_G4_ar.json --mu-user-range 0:1 \
    > goldens/cal_mu1.log 2>&1 || exit 3
  ( runcase cal_su goldens/cal_su ) & ( runcase cal_mu1 goldens/cal_mu1 ) & wait
  python3 tools/s81_dv/tokfunc/mu_stats.py --calibrate $O/cal_su/run.log.gz $O/cal_mu1/run.log.gz --out $O/cal.json \
    > $O/cal.txt 2>&1 || { touch $O/DONE_build_FAILED; exit 3; }
  touch $O/DONE_build ;;
run)
  c=$2; L=$(lat); G=goldens/$c
  case $c in
    su)       $GEN --lat $L --out $G ;;
    ar50r)    $GEN --lat $L --out $G --mu-users 50 --mu-mode real --mu-cal $CAL/calendar_rel241_G4_ar.json ;;
    mtp10r)   $GEN --lat $L --out $G --mu-users 10 --mu-mode real --mu-cal $CAL/calendar_rel241_G4_mtp.json ;;
    ar50r_c*) k=${c#ar50r_c}; $GEN --lat $L --out $G --mu-users 50 --mu-mode real --mu-cal $CAL/calendar_rel241_G4_ar.json \
                --mu-user-range $((5*k)):$((5*k+6)) ;;
    mtp10r_u*) k=${c#mtp10r_u}; $GEN --lat $L --out $G --mu-users 10 --mu-mode real --mu-cal $CAL/calendar_rel241_G4_mtp.json \
                --mu-user-range $k:$((k+1)) ;;
    ar50d)    $GEN --lat $L --out $G --mu-users 50 --mu-mode dense ;;
    mtp10d)   $GEN --lat $L --out $G --mu-users 10 --mu-mode dense ;;
    hop_*)    $GEN --lat $L --out $G --mu-hop-plan plans/${c#hop_}.json ;;
    *) echo "unknown case $c"; exit 2 ;;
  esac > $G.log 2>&1 || { echo "GEN_FAILED $c" > $O/$c.txt; cat $G.log >> $O/$c.txt; touch $O/DONE_$c; exit 3; }
  runcase $c $G ;;
esac
