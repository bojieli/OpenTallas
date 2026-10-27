#!/bin/bash
# S81-CORE-LAT-R14: submit_slice.sh FAMDIR CORE SUFFIX [HOSTS] -- 12.3 kit from a PASS family slice (checks.json), check-kit,
# ot-run finish build (kit rsynced to the target host first; collect from that host).  Generalises R13 submit_pass_slices.sh (fixed fam/ + r13).
set -euo pipefail
FD=$1; m=$2; SUF=$3; HOSTS=${4:-intel1}
W=/srv/opentallas-scratch2/claude/core-lat-r13-1027; R=/srv/opentallas-scratch2/claude/wt/s81-core-lat-r13; cd $R
d=$FD/$m; grep -q "\"verdict\": \"PASS\"" $d/checks.json || { echo "NOT PASS $m"; exit 2; }
rec=$m; [ $m = dsdv_gunit_l5 ] && rec=dsdv_gunit_l5_n32
k=$W/kits/${m}_$SUF; [ -d $k ] && { echo "EXISTS $k"; exit 3; }
python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py --module $rec --out $W/kits --suffix $SUF --master-slice $d/slice > $W/kits/gen_${m}_$SUF.log 2>&1 || { echo "GEN FAIL $m"; tail -5 $W/kits/gen_${m}_$SUF.log; exit 4; }
python3 tools/die_plan/master_slice.py check-kit $k --out $k/check_kit.json > $W/kits/checkkit_${m}_$SUF.log 2>&1 || { echo "CHECK_KIT FAIL $m"; tail -5 $W/kits/checkkit_${m}_$SUF.log; exit 5; }
mem=16; for h in ${HOSTS//,/ }; do [ $h = intel2 ] || rsync -a $k/ $h:$k/; done   # kit is self-contained (mounted at /work)
nohup ~/.local/bin/ot-run --mem $mem --threads 16 --hosts $HOSTS --dir $k -- bash $k/run_kit.sh $k finish $mem 16 > $W/kits/build_${m}_$SUF.otrun.log 2>&1 < /dev/null &
sleep 8; echo "SUBMITTED $m $k"; tail -3 $W/kits/build_${m}_$SUF.otrun.log
