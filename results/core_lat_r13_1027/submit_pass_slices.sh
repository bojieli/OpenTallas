#!/bin/bash
# R13: for every family slice whose automated checks PASS: 12.3 kit from the slice, check-kit, ot-run finish build
W=/srv/opentallas-scratch2/claude/core-lat-r13-1027; R=/srv/opentallas-scratch2/claude/wt/s81-core-lat-r13; cd $R
for d in $W/fam/*/; do m=$(basename $d); [ -f $d/checks.json ] || continue
  grep -q '"verdict": "PASS"' $d/checks.json || continue
  rec=$m; [ $m = dsdv_gunit_l5 ] && rec=dsdv_gunit_l5_n32
  [ -d $W/kits/${m}_r13 ] && continue
  python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py --module $rec --out $W/kits --suffix r13 --master-slice $d/slice > $W/kits/gen_$m.log 2>&1 || { echo "GEN FAIL $m"; continue; }
  k=$(ls -d $W/kits/${m}_r13 2>/dev/null) || { echo "NOKIT $m"; continue; }
  python3 tools/die_plan/master_slice.py check-kit $k --out $k/check_kit.json > /dev/null 2>&1 || { echo "CHECK_KIT FAIL $m"; continue; }
  mem=16; nohup ~/.local/bin/ot-run --mem $mem --threads 16 --dir $W/kits -- bash $k/run_kit.sh $k finish $mem 16 > $W/kits/build_$m.otrun.log 2>&1 < /dev/null &
  sleep 3; echo "SUBMITTED $m $(tail -1 $W/kits/build_$m.otrun.log)"
done
