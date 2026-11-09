#!/bin/bash
# QC-TYPES-11: strict bind at the staged wave path, compare with the proved bind, then advisory dry kit-rtl..gen on rows.
set -u
W=/srv/opentallas-scratch2/claude/qct11/wave; S=$W/src; Q=/srv/opentallas-scratch3/claude/qct11/start
until grep -q "^[0-9a-f]\{12\}$" $Q/stage6.log; do sleep 20; done
tail -3 $Q/stage6.log
P=$W/plan/plan_qc53v4nS.json; B=$W/bind_v4nS; L=$W/bind_logs; A=$S/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3.json
mkdir -p $L; cd $S
python3 -I -B -c "import sys,runpy;sys.path.insert(0,'$S/tools/die_plan');sys.argv=['schema.py','validate','$P'];runpy.run_path('$S/tools/die_plan/schema.py',run_name='__main__')" > $L/validate.log 2>&1; echo "VALIDATE rc $?"
mkdir -p $B
python3 -I -B tools/die_plan/bind.py elab $P --out $B --asbuilt $A > $L/elab.log 2>&1; echo "ELAB rc $?"
python3 -I -B tools/die_plan/bind.py bind $P --out $B --strict --all-gaps --asbuilt $A > $L/bind.log 2>&1; echo "BIND rc $?"
python3 -I -c "import json;r=json.load(open('$B/bind_report.json'));print('n_errors',r['n_errors'])"
n=0; d=0; for f in $B/rtl/*.sv; do n=$((n+1)); cmp -s $f $Q/bind_v4nS/rtl/$(basename $f) || d=$((d+1)); done; echo "RTL_SV total $n differ_from_proved $d"
SC=$S/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar.json
for T in slw_fe_v2__clf110fab2 coll_ft__cla4a; do :; done
for T in "$@"; do
  D=$W/dry/$T; mkdir -p $D/logs
  python3 -B tools/die_plan/bind.py kit-rtl $P --out $B --asbuilt $A --type $T --kit $D/rtl > $D/logs/kit_rtl.log 2>&1; echo "$T KIT_RTL rc $?"
  python3 -B tools/die_plan/gen.py phys $P --out $D/gen --types $T --rtl-root $S --kit-rtl $T=$D/rtl/kit_rtl.f --hold-ff-margin 0 --max-wire-um 120 --clock-landing $SC > $D/logs/gen.log 2>&1; echo "$T GEN rc $?"
  ls $D/gen/$T/config.mk 2>&1
  tail -2 $D/logs/gen.log | cut -c1-240
done
echo CHAIN_END
